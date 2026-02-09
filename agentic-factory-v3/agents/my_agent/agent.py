"""
My Agent Agent – uses RegulatedAgent from SDK.

Copy this my_agent to create a new agent.
Replace all "my_agent" references with your agent name.
"""

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
from org_agent_sdk.agent_capabilities import get_all_agents_list

AGENT_ID = "my_agent"  # Change this to your agent ID


class MyAgent:
    """
    My Agent Agent using RegulatedAgent SDK.
    
    What this agent does
    All actions are governed by the factory (tools, policies, audit).
    """

    def __init__(self, control_plane_url: str | None = None):
        """
        Initialize the my_agent agent.
        
        Args:
            control_plane_url: Optional control-plane URL (defaults to env var)
        """
        # Initialize regulated agent (loads definition, checks kill-switch)
        self.regulated = RegulatedAgent(
            agent_id=AGENT_ID,
            control_plane_url=control_plane_url
        )
        self.agent_client = AgentClient(base_url=control_plane_url)
        # Bounded conversation history so the agent can track the dialogue (included in LLM context)
        self.conversation = ConversationBuffer(max_messages=20)

        # Register tool implementations
        self._register_tools()

    def _register_tools(self):
        """Register tool implementations with ToolGateway."""
        # Register your allowed tools:
        # TODO: Register implementation for 'get_customer_profile'
        # TODO: Register implementation for 'check_risk_score'
        # Example:
        # from tools.mcp_my_tools import my_tool
        # self.regulated.tools.register_impl("my_tool", my_tool)
        pass

    def process(self, input_data: str) -> dict:
        """
        Main agent method - process input.
        
        Args:
            input_data: Input to process
        
        Returns:
            Dict with processing results
        """
        # Check if LLM is available
        if not self.regulated.llm:
            raise RuntimeError(
                "LLM not available. Set GOOGLE_API_KEY environment variable and ensure "
                "google-genai is installed: pip install google-genai"
            )
        
        # Step 1: Fetch data (tools)
        # TODO: Use tools to fetch data
        # Example:
        # my_tool = self.regulated.tools.get("my_tool")
        # data_json = my_tool(input_data)
        # data = json.loads(data_json)
        
        # Audit tool call
        # self.regulated.audit.log_tool_call(
        #     agent_id=self.regulated.agent_id,
        #     tool_name="my_tool",
        #     args={"input": input_data},
        #     result_summary=data_json[:200]
        # )
        
        # Step 2: Use LLM to analyze
        llm_prompt = f"""You are a [role]. Analyze this input and suggest action.

Input:
{input_data}

Based on this information, analyze and suggest the best action.
Respond with:
- decision: one of ["action1", "action2", "action3"]
- confidence: float between 0.0 and 1.0
- evidence: array of strings explaining your reasoning
"""
        
        reasoning = self.regulated.llm.reason(llm_prompt, context={
            "input": input_data,
            "agent_id": self.regulated.agent_id
        })
        
        suggested_action = reasoning.get("decision", "default_action")
        confidence = reasoning.get("confidence", 0.5)
        evidence = reasoning.get("evidence", [])
        
        # Step 3: Check policy (if needed)
        policy_result = None
        if suggested_action == "action_requiring_policy":
            try:
                policy_result = self.regulated.policy.evaluate("domain/policy", {
                    "param1": "value1"
                })
                
                if not policy_result.get("allowed"):
                    suggested_action = "fallback_action"
                    evidence.append(f"Policy denied: {policy_result.get('reason', 'N/A')}")
            except Exception as e:
                suggested_action = "fallback_action"
                policy_result = {"allowed": False, "reason": str(e)}
            
            # Audit policy check
            self.regulated.audit.log_policy_check(
                agent_id=self.regulated.agent_id,
                policy_id="domain/policy",
                input_data={"param1": "value1"},
                result=policy_result or {}
            )
        
        # Step 4: Execute action (if needed)
        # TODO: Execute your action
        
        # Step 5: Audit decision
        decision = f"Processed input, suggested {suggested_action}"
        self.regulated.audit.log_decision(
            agent_id=self.regulated.agent_id,
            decision=decision,
            context={
                "input": input_data,
                "suggested_action": suggested_action,
                "confidence": confidence,
                "evidence": evidence,
                "llm_reasoning": reasoning
            }
        )
        
        return {
            "status": "success",
            "suggested_action": suggested_action,
            "confidence": confidence,
            "evidence": evidence,
            "llm_reasoning": reasoning,
            "policy_check": policy_result
        }

    def answer(self, user_input: str) -> str | None:
        """
        Handle a question or command interactively. Returns None for quit.
        Supports: help, quit, mesh / list agents, agent <id>. Uses LLM when available for conversation.
        Keeps a bounded conversation history so the agent can refer to earlier turns.
        """
        raw = user_input.strip()
        if not raw:
            return self.conversation.record_response(
                "Try: 'help', 'mesh', 'list agents', or ask anything (LLM will respond if enabled)."
            )

        # Append current user message and get prior turns for LLM context
        self.conversation.append_user(raw)
        conv_ctx = self.conversation.context_for_llm(exclude_last=1)

        lower = raw.lower()
        if lower in ("quit", "exit", "q"):
            return None

        if lower == "help":
            help_text = (
                "My Agent Agent – interactive session.\n\n"
                "Commands:\n"
                "  mesh / list agents – List all agents in the mesh\n"
                "  agent <id>         – Show mesh card for an agent\n"
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
                try:
                    _root = Path(__file__).resolve().parent.parent.parent
                    agents = get_all_agents_list(_root)
                    agents = [{"agent_id": a["agent_id"], "domain": a.get("domain"), "purpose": a.get("purpose", "")} for a in agents]
                except Exception:
                    agents = []
            if not agents:
                return self.conversation.record_response("No agents in mesh (control-plane may be offline).")
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

        # LLM conversation (with recent context so the agent can track the dialogue)
        if self.regulated.llm:
            try:
                prompt = "You are a helpful agent. Respond in a clear, concise way."
                if conv_ctx:
                    prompt += f"\n\nRecent conversation (for context):\n{conv_ctx}\n\n"
                prompt += f"\nCurrent user message: {raw}"
                out = self.regulated.llm.explain(prompt)
                return self.conversation.record_response(out)
            except Exception as e:
                return self.conversation.record_response(f"I couldn't generate a response: {e}")
        return self.conversation.record_response(
            "I don't have an LLM configured. Set model in config and GOOGLE_API_KEY for conversation."
        )


# Factory function
def create_agent(control_plane_url: str | None = None) -> MyAgent:
    """
    Factory function to create MyAgent instance.
    
    Args:
        control_plane_url: Optional control-plane URL
    
    Returns:
        MyAgent instance
    """
    return MyAgent(control_plane_url=control_plane_url)
