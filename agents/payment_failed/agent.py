"""
Payment Failed Agent – uses RegulatedAgent from SDK.

This agent:
- Loads definition from Agent Registry
- Uses only allowed tools via ToolGateway
- Enforces policies via PolicyClient
- Audits all actions via AuditClient
"""

import re
import sys
import json
from pathlib import Path

# Add repo root and agent-sdk to path for imports
repo_root = Path(__file__).resolve().parent.parent.parent
agent_sdk_dir = repo_root / "agent-sdk"
for d in (repo_root, agent_sdk_dir):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

# Import from org_agent_sdk (since agent-sdk has hyphen, we import from the subpackage directly)
from org_agent_sdk import RegulatedAgent, AgentClient, ConversationBuffer

AGENT_ID = "payment_failed"


class PaymentFailedAgent:
    """
    Payment Failed Agent using RegulatedAgent SDK.
    
    This agent explains payment failures and suggests resolutions.
    All actions are governed by the factory (tools, policies, audit).
    """

    def __init__(self, control_plane_url: str | None = None):
        """
        Initialize the payment failed agent.
        
        Args:
            control_plane_url: Optional control-plane URL (defaults to env var)
        """
        # Initialize regulated agent (loads definition, checks kill-switch)
        self.regulated = RegulatedAgent(
            agent_id=AGENT_ID,
            control_plane_url=control_plane_url
        )
        self.agent_client = AgentClient(base_url=control_plane_url)
        self.conversation = ConversationBuffer(max_messages=20)

        # Register tool implementations
        self._register_tools()

    def _register_tools(self):
        """Register tool implementations with ToolGateway."""
        from tools.mcp_payment_tools import (
            get_payment_exception,
            suggest_payment_resolution,
            execute_payment_retry,
        )
        from tools.mcp_customer_tools import get_customer_profile

        self.regulated.tools.register_impl("get_payment_exception", get_payment_exception)
        self.regulated.tools.register_impl("suggest_payment_resolution", suggest_payment_resolution)
        self.regulated.tools.register_impl("execute_payment_retry", execute_payment_retry)
        self.regulated.tools.register_impl("get_customer_profile", get_customer_profile)

    def investigate_payment_exception(self, exception_id: str) -> dict:
        """
        Investigate a payment exception using LLM reasoning.
        
        This method:
        1. Fetches exception details (tool)
        2. Fetches customer profile (tool)
        3. Uses LLM to analyze and suggest resolution
        4. Checks policy if retry is suggested
        5. Audits all actions
        
        Args:
            exception_id: Exception identifier (e.g. "EX-2025-001")
        
        Returns:
            Dict with investigation results including LLM reasoning
        """
        # Check if LLM is available
        if not self.regulated.llm:
            raise RuntimeError(
                "LLM not available. Set GOOGLE_API_KEY environment variable and ensure "
                "google-generativeai is installed: pip install google-generativeai"
            )
        
        # Step 1: Fetch exception details (tool)
        get_exception = self.regulated.tools.get("get_payment_exception")
        exception_json = get_exception(exception_id)
        exception_data = json.loads(exception_json)
        
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="get_payment_exception",
            args={"exception_id": exception_id},
            result_summary=exception_json[:200]
        )
        
        if "error" in exception_data:
            return {
                "status": "error",
                "error": exception_data["error"],
                "exception_id": exception_id
            }
        
        # Step 2: Fetch customer profile (tool)
        customer_id = exception_data.get("customer_id")
        customer_data = {}
        if customer_id:
            get_customer = self.regulated.tools.get("get_customer_profile")
            customer_json = get_customer(customer_id)
            customer_data = json.loads(customer_json)
            
            self.regulated.audit.log_tool_call(
                agent_id=self.regulated.agent_id,
                tool_name="get_customer_profile",
                args={"customer_id": customer_id},
                result_summary=customer_json[:200]
            )
        
        # Step 3: Use LLM to analyze and suggest resolution (AI reasoning)
        llm_prompt = f"""You are a payment exception analyst. Analyze this payment exception and suggest the best resolution action.

Payment Exception Details:
{json.dumps(exception_data, indent=2)}

Customer Profile:
{json.dumps(customer_data, indent=2) if customer_data else "Not available"}

Based on this information, analyze:
1. What went wrong? (Explain the failure reason)
2. What is the best resolution action? (Choose: retry, escalate, or waive_fee)
3. Why is this the best action? (Provide reasoning)
4. What is your confidence level? (0.0 to 1.0)

Consider:
- The failure reason and amount
- Customer status and history
- Previous retry attempts
- Risk factors

Respond with:
- decision: one of "retry", "escalate", or "waive_fee"
- confidence: float between 0.0 and 1.0
- evidence: array of strings explaining your reasoning
"""
        
        # Get LLM reasoning
        reasoning = self.regulated.llm.reason(llm_prompt, context={
            "exception_id": exception_id,
            "agent_id": self.regulated.agent_id
        })
        
        suggested_action = reasoning.get("decision", "escalate")
        confidence = reasoning.get("confidence", 0.5)
        evidence = reasoning.get("evidence", [])
        
        # Step 4: Check policy if retry is suggested (governance)
        policy_result = None
        if suggested_action == "retry":
            try:
                policy_result = self.regulated.policy.evaluate("payments/retry", {
                    "amount": exception_data.get("amount", 0),
                    "previous_retries": exception_data.get("retry_count", 0),
                    "beneficiary_blocked": False
                })
                
                # If policy denies retry, override LLM decision
                if not policy_result.get("allowed"):
                    suggested_action = "escalate"
                    evidence.append(f"Policy check denied retry: {policy_result.get('reason', 'N/A')}")
            except Exception as e:
                # Policy check failed, default to escalate
                suggested_action = "escalate"
                policy_result = {"allowed": False, "reason": str(e)}
                evidence.append(f"Policy check failed: {str(e)}")
            
            # Log policy check
            self.regulated.audit.log_policy_check(
                agent_id=self.regulated.agent_id,
                policy_id="payments/retry",
                input_data={
                    "amount": exception_data.get("amount", 0),
                    "previous_retries": exception_data.get("retry_count", 0)
                },
                result=policy_result or {}
            )
        
        # Step 5: Suggest resolution (tool)
        resolution_suggestion = None
        if suggested_action:
            suggest_resolution = self.regulated.tools.get("suggest_payment_resolution")
            reason_text = ". ".join(evidence) if evidence else f"LLM reasoning: {reasoning.get('decision', 'N/A')}"
            
            resolution_json = suggest_resolution(
                exception_id=exception_id,
                suggested_action=suggested_action,
                reason=reason_text
            )
            resolution_suggestion = json.loads(resolution_json)
            
            self.regulated.audit.log_tool_call(
                agent_id=self.regulated.agent_id,
                tool_name="suggest_payment_resolution",
                args={
                    "exception_id": exception_id,
                    "suggested_action": suggested_action
                },
                result_summary=resolution_json[:200]
            )
        
        # Step 6: Log decision (audit)
        decision = f"Investigated exception {exception_id}, LLM suggested {suggested_action} (confidence: {confidence:.2f})"
        self.regulated.audit.log_decision(
            agent_id=self.regulated.agent_id,
            decision=decision,
            context={
                "exception_id": exception_id,
                "failure_reason": exception_data.get("failure_reason"),
                "suggested_action": suggested_action,
                "confidence": confidence,
                "evidence": evidence,
                "llm_reasoning": reasoning
            }
        )
        
        return {
            "status": "success",
            "exception": exception_data,
            "customer": customer_data if customer_id else None,
            "suggested_action": suggested_action,
            "confidence": confidence,
            "evidence": evidence,
            "llm_reasoning": reasoning,
            "resolution_suggestion": resolution_suggestion,
            "policy_check": policy_result
        }

    def explain_payment_failure(self, exception_id: str) -> str:
        """
        Explain a payment failure using LLM to generate human-readable explanation.
        
        Args:
            exception_id: Exception identifier
        
        Returns:
            Human-readable explanation generated by LLM
        """
        # Check if LLM is available
        if not self.regulated.llm:
            raise RuntimeError(
                "LLM not available. Set GOOGLE_API_KEY environment variable and ensure "
                "google-generativeai is installed: pip install google-generativeai"
            )
        
        # Investigate exception (gets data + LLM reasoning)
        result = self.investigate_payment_exception(exception_id)
        
        if result["status"] == "error":
            return f"Error: {result['error']}"
        
        # Use LLM to generate explanation
        exception = result["exception"]
        customer = result.get("customer", {})
        reasoning = result.get("llm_reasoning", {})
        
        explanation_prompt = f"""Explain this payment failure in clear, human-readable terms for a customer service colleague.

Payment Exception:
{json.dumps(exception, indent=2)}

Customer Information:
{json.dumps(customer, indent=2) if customer else "Not available"}

Analysis:
- Suggested Action: {result.get('suggested_action', 'N/A')}
- Confidence: {result.get('confidence', 0.0):.1%}
- Evidence: {', '.join(result.get('evidence', []))}

Write a clear, concise explanation that:
1. Explains what went wrong in simple terms
2. Describes the suggested resolution
3. Provides context for why this action was recommended
4. Notes any important considerations

Keep it professional and easy to understand.
"""
        
        explanation = self.regulated.llm.explain(explanation_prompt, context={
            "exception_id": exception_id,
            "investigation_result": result
        })
        
        return explanation

    def retry_payment(self, exception_id: str, force: bool = False) -> dict:
        """
        Execute a payment retry for a failed payment exception.
        
        This method:
        1. Investigates the exception (fetches data, LLM reasoning, policy checks)
        2. If retry is suggested and allowed, executes the retry
        3. Audits the retry execution
        
        Args:
            exception_id: Exception identifier (e.g. "EX-2025-001")
            force: If True, skip investigation and policy checks (use with caution)
        
        Returns:
            Dict with retry execution result
        """
        # Step 1: Investigate exception (unless forced)
        if not force:
            investigation = self.investigate_payment_exception(exception_id)
            
            if investigation["status"] == "error":
                return {
                    "status": "error",
                    "error": investigation.get("error"),
                    "exception_id": exception_id
                }
            
            suggested_action = investigation.get("suggested_action")
            policy_check = investigation.get("policy_check", {})
            
            # Check if retry is suggested
            if suggested_action != "retry":
                return {
                    "status": "skipped",
                    "exception_id": exception_id,
                    "reason": f"Agent suggested action: {suggested_action}, not retry",
                    "investigation": investigation
                }
            
            # Check if policy allows retry
            if policy_check and not policy_check.get("allowed"):
                return {
                    "status": "denied",
                    "exception_id": exception_id,
                    "reason": f"Policy check denied retry: {policy_check.get('reason', 'N/A')}",
                    "investigation": investigation
                }
            
            exception_data = investigation.get("exception", {})
            amount = exception_data.get("amount")
            evidence = investigation.get("evidence", [])
            reason = ". ".join(evidence) if evidence else "Agent-initiated retry after investigation"
        else:
            # Force mode: skip investigation
            get_exception = self.regulated.tools.get("get_payment_exception")
            exception_json = get_exception(exception_id)
            exception_data = json.loads(exception_json)
            amount = exception_data.get("amount")
            reason = "Force retry (investigation skipped)"
        
        # Step 2: Execute retry (tool)
        execute_retry = self.regulated.tools.get("execute_payment_retry")
        retry_result_json = execute_retry(
            exception_id=exception_id,
            amount=amount,
            reason=reason
        )
        retry_result = json.loads(retry_result_json)
        
        # Step 3: Audit retry execution
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="execute_payment_retry",
            args={
                "exception_id": exception_id,
                "amount": amount,
                "force": force
            },
            result_summary=retry_result_json[:200]
        )
        
        # Step 4: Log decision
        decision = f"Executed payment retry for exception {exception_id}. Status: {retry_result.get('status', 'unknown')}"
        self.regulated.audit.log_decision(
            agent_id=self.regulated.agent_id,
            decision=decision,
            context={
                "exception_id": exception_id,
                "retry_result": retry_result,
                "force": force
            }
        )
        
        return {
            "status": retry_result.get("status"),
            "exception_id": exception_id,
            "retry_id": retry_result.get("retry_id"),
            "message": retry_result.get("message") or retry_result.get("error"),
            "retry_result": retry_result
        }

    def answer(self, user_input: str) -> str | None:
        """
        Handle a question or command interactively. Returns None for quit.
        Supports: help, quit, investigate <id>, explain <id>, retry <id>, mesh, list agents, agent <id>.
        Keeps a bounded conversation history for LLM context.
        """
        raw = user_input.strip()
        if not raw:
            return self.conversation.record_response(
                "Try: 'help', 'investigate EX-2025-001', 'explain EX-2025-001', 'retry EX-2025-001', 'mesh', or 'list agents'."
            )

        self.conversation.append_user(raw)
        conv_ctx = self.conversation.context_for_llm(exclude_last=1)

        lower = raw.lower()
        if lower in ("quit", "exit", "q"):
            return None

        if lower == "help":
            help_text = (
                "Payment Failed Agent – I investigate payment exceptions and suggest resolutions.\n\n"
                "Commands:\n"
                "  investigate <id>  – Full investigation (e.g. EX-2025-001)\n"
                "  explain <id>      – Human-readable explanation\n"
                "  retry <id>        – Execute retry (after investigation and policy check)\n"
                "  mesh / list agents – List all agents in the mesh\n"
                "  agent <id>        – Show mesh card for an agent\n"
                "  help              – This message\n"
                "  quit / exit       – End session\n"
            )
            if self.regulated.llm:
                help_text += "\n(LLM enabled – you can also ask in natural language. I keep context of our conversation.)"
            return self.conversation.record_response(help_text)

        # Mesh: list agents
        if lower in ("mesh", "list agents", "agents"):
            agents = self.agent_client.list_mesh_agents()
            if not agents:
                return self.conversation.record_response("No agents in mesh (is the control-plane running?).")
            lines = ["Agents in the mesh:"]
            for a in agents:
                pid = a.get("agent_id", "")
                domain = a.get("domain", "")
                purpose = (a.get("purpose") or "")[:60]
                lines.append(f"  • {pid} ({domain}): {purpose}...")
            return self.conversation.record_response("\n".join(lines))

        # Mesh card for one agent
        if lower.startswith("agent ") or lower.startswith("card "):
            parts = raw.split()
            if len(parts) >= 2:
                agent_id = parts[1]
                card = self.agent_client.get_mesh_agent(agent_id)
                if not card:
                    return self.conversation.record_response(f"Agent not found: {agent_id}")
                return self.conversation.record_response(json.dumps(card, indent=2))
            return self.conversation.record_response("Usage: agent <agent_id> or card <agent_id>")

        # Exception ID for investigate / explain / retry
        ex_match = re.search(r"EX-\d+-\d+", raw, re.IGNORECASE)
        exception_id = ex_match.group(0) if ex_match else None

        if exception_id and ("investigate" in lower or "check" in lower or "look" in lower):
            try:
                result = self.investigate_payment_exception(exception_id)
                if self.regulated.llm:
                    prompt = "Summarize this payment investigation for the user."
                    if conv_ctx:
                        prompt += f"\n\nRecent conversation:\n{conv_ctx}\n\n"
                    prompt += f"\nResult:\n{json.dumps(result, indent=2)}"
                    return self.conversation.record_response(self.regulated.llm.explain(prompt))
                return self.conversation.record_response(json.dumps(result, indent=2))
            except Exception as e:
                return self.conversation.record_response(f"Investigation failed: {e}")

        if exception_id and "explain" in lower:
            try:
                return self.conversation.record_response(self.explain_payment_failure(exception_id))
            except Exception as e:
                return self.conversation.record_response(f"Explain failed: {e}")

        if exception_id and "retry" in lower:
            try:
                result = self.retry_payment(exception_id)
                return self.conversation.record_response(json.dumps(result, indent=2))
            except Exception as e:
                return self.conversation.record_response(f"Retry failed: {e}")

        # Fallback: if they gave an exception ID, investigate
        if exception_id:
            try:
                result = self.investigate_payment_exception(exception_id)
                if self.regulated.llm:
                    prompt = "Summarize this payment investigation."
                    if conv_ctx:
                        prompt += f"\n\nRecent conversation:\n{conv_ctx}\n\n"
                    prompt += f"\nResult:\n{json.dumps(result, indent=2)}"
                    return self.conversation.record_response(self.regulated.llm.explain(prompt))
                return self.conversation.record_response(json.dumps(result, indent=2))
            except Exception as e:
                return self.conversation.record_response(f"Error: {e}")

        # LLM fallback
        if self.regulated.llm:
            prompt = "You are the Payment Failed Agent. You investigate payment exceptions (e.g. EX-2025-001), explain failures, and suggest retries. "
            if conv_ctx:
                prompt += f"\n\nRecent conversation:\n{conv_ctx}\n\n"
            prompt += f"User said: {raw}. Reply briefly or suggest a command like 'investigate EX-2025-001'."
            try:
                return self.conversation.record_response(self.regulated.llm.explain(prompt))
            except Exception as e:
                return self.conversation.record_response(f"I didn't understand. Try 'help'. (LLM error: {e})")
        return self.conversation.record_response("I didn't understand. Try 'help' or 'investigate EX-2025-001'.")


# Create agent instance (for use by runtime)
def create_agent(control_plane_url: str | None = None) -> PaymentFailedAgent:
    """
    Factory function to create PaymentFailedAgent instance.
    
    Args:
        control_plane_url: Optional control-plane URL
    
    Returns:
        PaymentFailedAgent instance
    """
    return PaymentFailedAgent(control_plane_url=control_plane_url)


# For ADK compatibility (if needed)
try:
    from google.adk.agents import Agent
    
    def create_adk_agent(control_plane_url: str | None = None) -> Agent:
        """
        Create ADK Agent from RegulatedAgent (for Google ADK integration).
        
        Args:
            control_plane_url: Optional control-plane URL
        
        Returns:
            Google ADK Agent instance
        """
        payment_agent = PaymentFailedAgent(control_plane_url=control_plane_url)
        regulated = payment_agent.regulated
        
        # Resolve tools
        tools_dict = regulated.tools.resolve_tools()
        tool_callables = list(tools_dict.values())
        
        # Build instruction
        instruction = regulated.definition.get("purpose", {}).get("instructions_prefix", "")
        instruction += f"\n\nYour role: {regulated.purpose}"
        instruction += "\n\nWhen the user provides a payment exception ID (e.g. EX-2025-001), investigate it thoroughly and suggest appropriate resolutions."
        
        return Agent(
            model=regulated.definition.get("model", "gemini-1.5-pro"),
            name=regulated.definition.get("name", AGENT_ID),
            description=regulated.purpose[:200],
            instruction=instruction,
            tools=tool_callables,
        )
except ImportError:
    # ADK not available, skip ADK integration
    def create_adk_agent(control_plane_url: str | None = None):
        """ADK not available."""
        raise ImportError("google-adk not installed. Install with: pip install google-adk")
