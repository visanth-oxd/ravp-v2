"""
Fraud Detection Agent – detects fraudulent patterns and interacts with payment_failed agent.
"""

import re
import sys
import json
from pathlib import Path

# Add repo root and agent-sdk to path
repo_root = Path(__file__).resolve().parent.parent.parent
agent_sdk_dir = repo_root / "agent-sdk"
for d in (repo_root, agent_sdk_dir):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

from org_agent_sdk import RegulatedAgent, AgentClient, ConversationBuffer

AGENT_ID = "fraud_detection"


class FraudDetectionAgent:
    """
    Fraud Detection Agent using RegulatedAgent SDK.
    
    This agent detects fraudulent payment patterns and can interact with
    other agents (e.g., payment_failed) to coordinate responses.
    """

    def __init__(self, control_plane_url: str | None = None):
        """Initialize the fraud detection agent."""
        self.regulated = RegulatedAgent(
            agent_id=AGENT_ID,
            control_plane_url=control_plane_url
        )
        
        # Initialize agent client for agent-to-agent interaction
        self.agent_client = AgentClient(base_url=control_plane_url)
        self.conversation = ConversationBuffer(max_messages=20)

        # Register tool implementations
        self._register_tools()

    def _register_tools(self):
        """Register tool implementations with ToolGateway."""
        from tools.mcp_fraud_tools import (
            get_transaction_history,
            check_risk_score,
            flag_suspicious_account,
        )
        from tools.mcp_payment_tools import get_payment_exception
        from tools.mcp_customer_tools import get_customer_profile

        self.regulated.tools.register_impl("get_transaction_history", get_transaction_history)
        self.regulated.tools.register_impl("check_risk_score", check_risk_score)
        self.regulated.tools.register_impl("flag_suspicious_account", flag_suspicious_account)
        self.regulated.tools.register_impl("get_payment_exception", get_payment_exception)
        self.regulated.tools.register_impl("get_customer_profile", get_customer_profile)

    def analyze_for_fraud(self, exception_id: str) -> dict:
        """
        Analyze a payment exception for fraud indicators.
        
        This method:
        1. Fetches exception and customer data
        2. Gets transaction history
        3. Uses LLM to analyze fraud patterns
        4. Checks risk score
        5. Checks policies
        6. Can interact with payment_failed agent
        
        Args:
            exception_id: Payment exception identifier
        
        Returns:
            Dict with fraud analysis results
        """
        if not self.regulated.llm:
            raise RuntimeError("LLM not available. Set GOOGLE_API_KEY environment variable.")
        
        # Step 1: Fetch exception data
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
        
        # Step 2: Fetch customer data
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
        
        # Step 3: Get transaction history
        get_history = self.regulated.tools.get("get_transaction_history")
        history_json = get_history(customer_id, days=30)
        history_data = json.loads(history_json)
        
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="get_transaction_history",
            args={"customer_id": customer_id, "days": 30},
            result_summary=history_json[:200]
        )
        
        # Step 4: Check risk score
        check_risk = self.regulated.tools.get("check_risk_score")
        risk_json = check_risk(customer_id, exception_id)
        risk_data = json.loads(risk_json)
        
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="check_risk_score",
            args={"customer_id": customer_id, "transaction_id": exception_id},
            result_summary=risk_json[:200]
        )
        
        # Step 5: Use LLM to analyze fraud patterns
        llm_prompt = f"""You are a fraud detection analyst. Analyze this payment exception for fraud indicators.

Payment Exception:
{json.dumps(exception_data, indent=2)}

Customer Profile:
{json.dumps(customer_data, indent=2) if customer_data else "Not available"}

Transaction History:
{json.dumps(history_data, indent=2)}

Risk Score: {risk_data.get('risk_score', 0.0)} ({risk_data.get('risk_tier', 'unknown')})

Analyze for fraud indicators:
1. Are there suspicious patterns? (multiple failures, location changes, etc.)
2. What is the fraud risk level? (low, medium, high)
3. What action should be taken? (monitor, flag, block)
4. Should payment retry be allowed? (yes, no, conditional)

Respond with:
- decision: one of "monitor", "flag", "block"
- fraud_risk: "low" | "medium" | "high"
- allow_retry: true | false
- confidence: float between 0.0 and 1.0
- evidence: array of strings explaining fraud indicators
"""
        
        reasoning = self.regulated.llm.reason(llm_prompt, context={
            "exception_id": exception_id,
            "customer_id": customer_id,
            "risk_score": risk_data.get("risk_score")
        })
        
        fraud_decision = reasoning.get("decision", "monitor")
        fraud_risk = reasoning.get("fraud_risk", "low")
        allow_retry = reasoning.get("allow_retry", True)
        confidence = reasoning.get("confidence", 0.5)
        evidence = reasoning.get("evidence", [])
        
        # Step 6: Check policies
        policy_result = None
        if fraud_decision == "block":
            try:
                policy_result = self.regulated.policy.evaluate("fraud/block", {
                    "risk_score": risk_data.get("risk_score", 0.0),
                    "risk_factors": risk_data.get("risk_factors", [])
                })
                
                if not policy_result.get("allowed"):
                    fraud_decision = "flag"
                    evidence.append(f"Policy check denied block: {policy_result.get('reason', 'N/A')}")
            except Exception as e:
                fraud_decision = "flag"
                policy_result = {"allowed": False, "reason": str(e)}
        
        # Step 7: Flag account if needed
        flag_result = None
        if fraud_decision in ["flag", "block"]:
            flag_tool = self.regulated.tools.get("flag_suspicious_account")
            reason_text = ". ".join(evidence) if evidence else f"Fraud risk: {fraud_risk}"
            flag_json = flag_tool(customer_id, reason_text, risk_data.get("risk_score", 0.0))
            flag_result = json.loads(flag_json)
            
            self.regulated.audit.log_tool_call(
                agent_id=self.regulated.agent_id,
                tool_name="flag_suspicious_account",
                args={"customer_id": customer_id, "reason": reason_text},
                result_summary=flag_json[:200]
            )
        
        # Step 8: Interact with payment_failed agent if retry should be blocked
        payment_agent_result = None
        if not allow_retry:
            try:
                # Invoke payment_failed agent to inform it about fraud
                payment_agent_result = self.agent_client.invoke_agent(
                    "payment_failed",
                    "investigate_payment_exception",
                    exception_id=exception_id
                )
                
                # Log agent-to-agent interaction
                self.regulated.audit.log(
                    agent_id=self.regulated.agent_id,
                    event_type="agent_interaction",
                    payload={
                        "target_agent": "payment_failed",
                        "method": "investigate_payment_exception",
                        "reason": "Fraud detected - coordinating response",
                        "result": payment_agent_result
                    }
                )
            except Exception as e:
                payment_agent_result = {"status": "error", "error": str(e)}
        
        # Step 9: Audit decision
        decision = f"Analyzed exception {exception_id} for fraud. Decision: {fraud_decision}, Risk: {fraud_risk}, Allow Retry: {allow_retry}"
        self.regulated.audit.log_decision(
            agent_id=self.regulated.agent_id,
            decision=decision,
            context={
                "exception_id": exception_id,
                "customer_id": customer_id,
                "fraud_decision": fraud_decision,
                "fraud_risk": fraud_risk,
                "allow_retry": allow_retry,
                "confidence": confidence,
                "evidence": evidence,
                "risk_score": risk_data.get("risk_score"),
                "llm_reasoning": reasoning,
                "payment_agent_coordination": payment_agent_result
            }
        )
        
        return {
            "status": "success",
            "exception_id": exception_id,
            "customer_id": customer_id,
            "fraud_decision": fraud_decision,
            "fraud_risk": fraud_risk,
            "allow_retry": allow_retry,
            "confidence": confidence,
            "evidence": evidence,
            "risk_score": risk_data.get("risk_score"),
            "risk_tier": risk_data.get("risk_tier"),
            "llm_reasoning": reasoning,
            "policy_check": policy_result,
            "flag_result": flag_result,
            "payment_agent_coordination": payment_agent_result
        }


    def answer(self, user_input: str) -> str | None:
        """
        Handle a question or command interactively. Returns None for quit.
        Supports: help, quit, analyze <exception_id>, mesh, list agents, agent <id>, invoke <agent_id> <method> [args].
        Keeps a bounded conversation history for LLM context.
        """
        raw = user_input.strip()
        if not raw:
            return self.conversation.record_response(
                "Try: 'help', 'analyze EX-2025-001', 'mesh', 'list agents', 'agent payment_failed', or 'invoke payment_failed investigate_payment_exception EX-2025-001'."
            )

        self.conversation.append_user(raw)
        conv_ctx = self.conversation.context_for_llm(exclude_last=1)

        lower = raw.lower()
        if lower in ("quit", "exit", "q"):
            return None

        if lower == "help":
            help_text = (
                "Fraud Detection Agent – I analyze payment exceptions for fraud.\n\n"
                "Commands:\n"
                "  analyze <id> / fraud <id>  – Analyze exception (e.g. EX-2025-001) for fraud\n"
                "  mesh / list agents          – List all agents in the mesh\n"
                "  agent <id> / card <id>      – Show mesh card for an agent\n"
                "  invoke <agent> <method> [args] – Invoke another agent (e.g. invoke payment_failed investigate_payment_exception EX-2025-001)\n"
                "  help                        – This message\n"
                "  quit / exit                 – End session\n"
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

        # Invoke another agent: "invoke payment_failed investigate_payment_exception EX-2025-001"
        if lower.startswith("invoke "):
            parts = raw.split()
            if len(parts) >= 3:
                target_id = parts[1]
                method = parts[2]
                kwargs = {}
                if len(parts) > 3:
                    for p in parts[3:]:
                        if "=" in p:
                            k, v = p.split("=", 1)
                            kwargs[k.strip()] = v.strip()
                        else:
                            kwargs["exception_id"] = p
                try:
                    result = self.agent_client.invoke_agent(target_id, method, **kwargs)
                    return self.conversation.record_response(json.dumps(result, indent=2))
                except Exception as e:
                    return self.conversation.record_response(f"Invoke failed: {e}")
            return self.conversation.record_response("Usage: invoke <agent_id> <method> [exception_id=EX-2025-001]")

        # Analyze for fraud: "analyze EX-2025-001" or "fraud EX-2025-001"
        ex_match = re.search(r"EX-\d+-\d+", raw, re.IGNORECASE)
        if ex_match and ("analyze" in lower or "fraud" in lower or "check" in lower):
            exception_id = ex_match.group(0)
            try:
                result = self.analyze_for_fraud(exception_id)
                return self.conversation.record_response(json.dumps(result, indent=2))
            except Exception as e:
                return self.conversation.record_response(f"Analysis failed: {e}")

        # Extract exception ID for natural language
        if ex_match and self.regulated.llm:
            exception_id = ex_match.group(0)
            try:
                result = self.analyze_for_fraud(exception_id)
                prompt = "You are a fraud analyst. Summarize this fraud analysis for the user in clear language."
                if conv_ctx:
                    prompt += f"\n\nRecent conversation:\n{conv_ctx}\n\n"
                prompt += f"\nResult:\n{json.dumps(result, indent=2)}\n\nProvide a short summary and recommendation."
                return self.conversation.record_response(self.regulated.llm.explain(prompt))
            except Exception as e:
                return self.conversation.record_response(f"Analysis failed: {e}")

        # LLM fallback
        if self.regulated.llm:
            prompt = "You are the Fraud Detection Agent. You analyze payment exceptions for fraud and can invoke the payment_failed agent. Available: 'analyze EX-2025-001', 'mesh', 'invoke payment_failed investigate_payment_exception EX-2025-001'. "
            if conv_ctx:
                prompt += f"\n\nRecent conversation:\n{conv_ctx}\n\n"
            prompt += f"User said: {raw}. Reply briefly or suggest a command."
            try:
                return self.conversation.record_response(self.regulated.llm.explain(prompt))
            except Exception as e:
                return self.conversation.record_response(f"I didn't understand. Try 'help'. (LLM error: {e})")
        return self.conversation.record_response("I didn't understand. Try 'help' or 'analyze EX-2025-001'.")


def create_agent(control_plane_url: str | None = None) -> FraudDetectionAgent:
    """Factory function to create FraudDetectionAgent instance."""
    return FraudDetectionAgent(control_plane_url=control_plane_url)
