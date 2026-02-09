"""
Cloud Healing Agent – executes remediation actions on GCP resources.
Invoked by Cloud Reliability Agent via request_healing tool (agent-to-agent).
"""

import re
import sys
import json
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
agent_sdk_dir = repo_root / "agent-sdk"
for d in (repo_root, agent_sdk_dir):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

from org_agent_sdk import RegulatedAgent, AgentClient, ConversationBuffer
from org_agent_sdk.agent_capabilities import get_all_agents_list

AGENT_ID = "cloud_healing"


class CloudHealingAgent:
    """
    Healing Agent: resize Cloud SQL, restart instances, get instance details.
    Used by Cloud Reliability Agent when remediation requires an actionable change.
    """

    def __init__(self, control_plane_url: str | None = None):
        self.regulated = RegulatedAgent(
            agent_id=AGENT_ID,
            control_plane_url=control_plane_url,
        )
        self.agent_client = AgentClient(base_url=control_plane_url)
        self.conversation = ConversationBuffer(max_messages=20)
        self._register_tools()

    def _register_tools(self):
        from tools.mcp_healing_tools import (
            get_instance_details,
            resize_cloud_sql_instance,
            restart_instance,
        )
        self.regulated.tools.register_impl("get_instance_details", get_instance_details)
        self.regulated.tools.register_impl("resize_cloud_sql_instance", resize_cloud_sql_instance)
        self.regulated.tools.register_impl("restart_instance", restart_instance)

    def _audit_tool_call(
        self,
        tool_name: str,
        args: dict,
        result: str,
        extra_payload: dict | None = None,
    ) -> None:
        """Log tool call with optional extra fields (e.g. invoked_by) for traceability."""
        payload = {
            "tool": tool_name,
            "args_sanitized": args,
            "result_summary": result[:200] if result else "",
            "error": None,
        }
        if extra_payload:
            payload.update(extra_payload)
        self.regulated.audit.log(
            self.regulated.agent_id,
            "tool_call",
            payload,
        )

    def execute_action(
        self,
        action: str,
        target_type: str,
        target_id: str,
        params: dict | None = None,
        invoked_by: str | None = None,
    ) -> str:
        """
        Execute a healing action. Called via the Agent Invocation Gateway only.
        invoked_by is set by the gateway for audit traceability.
        Returns JSON string result.
        """
        params = params or {}
        audit_payload_extra = {"invoked_by": invoked_by} if invoked_by else {}

        if action == "get_instance_details":
            fn = self.regulated.tools.get("get_instance_details")
            out = fn(target_id)
            self._audit_tool_call("get_instance_details", {"instance_id": target_id}, out, audit_payload_extra)
            return out

        if action == "resize_cloud_sql_instance":
            new_tier = params.get("new_tier")
            if not new_tier:
                return json.dumps({"error": "new_tier required for resize_cloud_sql_instance", "target_id": target_id})
            fn = self.regulated.tools.get("resize_cloud_sql_instance")
            out = fn(instance_id=target_id, new_tier=new_tier)
            self._audit_tool_call("resize_cloud_sql_instance", {"instance_id": target_id, "new_tier": new_tier}, out, audit_payload_extra)
            return out

        if action == "restart_instance":
            fn = self.regulated.tools.get("restart_instance")
            out = fn(instance_id=target_id)
            self._audit_tool_call("restart_instance", {"instance_id": target_id}, out, audit_payload_extra)
            return out

        return json.dumps({
            "error": f"Unknown action: {action}",
            "allowed_actions": ["get_instance_details", "resize_cloud_sql_instance", "restart_instance"],
            "target_id": target_id,
        })

    def answer(self, user_input: str) -> str | None:
        """
        Handle a question or command interactively. Returns None for quit.
        Supports: help, quit, instance details, resize, restart, list agents (mesh).
        Keeps a bounded conversation history for LLM context.
        """
        raw = user_input.strip()
        if not raw:
            return self.conversation.record_response(
                "Try: 'help', 'instance cloud-sql-instance-1', 'resize cloud-sql-instance-1 db-n1-standard-4', 'restart cloud-sql-instance-1', 'mesh' or 'list agents'."
            )

        self.conversation.append_user(raw)
        conv_ctx = self.conversation.context_for_llm(exclude_last=1)

        lower = raw.lower()
        if lower in ("quit", "exit", "q"):
            return None

        if lower == "help":
            return self.conversation.record_response(
                "Cloud Healing Agent – I execute remediation on GCP resources.\n\n"
                "Commands:\n"
                "  instance [id]     – Get instance details (default: cloud-sql-instance-1)\n"
                "  resize <id> [tier] – Resize Cloud SQL (tier e.g. db-n1-standard-4)\n"
                "  restart <id>      – Restart instance\n"
                "  mesh / list agents – List agents in the mesh (who can invoke me)\n"
                "  help              – This message\n"
                "  quit / exit       – End session\n"
            )

        # Mesh: list agents (control-plane mesh API or file-based fallback)
        if lower in ("mesh", "list agents", "agents"):
            mesh_agents = self.agent_client.list_mesh_agents()
            if not mesh_agents:
                try:
                    _root = Path(__file__).resolve().parent.parent.parent
                    mesh_agents = get_all_agents_list(_root)
                    mesh_agents = [{"agent_id": a["agent_id"], "domain": a.get("domain"), "purpose": a.get("purpose", "")} for a in mesh_agents]
                except Exception:
                    mesh_agents = []
            if not mesh_agents:
                return self.conversation.record_response(
                    "No agents in mesh (control-plane may be offline; mesh list requires control-plane)."
                )
            lines = ["Agents in the mesh:"]
            for a in mesh_agents:
                pid = a.get("agent_id", "")
                domain = a.get("domain", "")
                purpose = (a.get("purpose") or "")[:60]
                lines.append(f"  • {pid} ({domain}): {purpose}...")
            return self.conversation.record_response("\n".join(lines))

        # Instance details
        instance_match = re.search(r"cloud-sql-instance-\d+|backend-service-[-\w]+", raw, re.IGNORECASE)
        instance_id = instance_match.group(0) if instance_match else "cloud-sql-instance-1"
        if "instance" in lower and ("detail" in lower or "get" in lower or lower.strip().startswith("instance")):
            out = self.execute_action("get_instance_details", "instance", instance_id)
            return self.conversation.record_response(out)

        # Resize
        tier_match = re.search(r"db-n1-(standard|highmem)-\d+", raw, re.IGNORECASE)
        new_tier = tier_match.group(0) if tier_match else "db-n1-standard-4"
        if "resize" in lower:
            out = self.execute_action("resize_cloud_sql_instance", "instance", instance_id, {"new_tier": new_tier})
            return self.conversation.record_response(out)

        # Restart
        if "restart" in lower:
            out = self.execute_action("restart_instance", "instance", instance_id)
            return self.conversation.record_response(out)

        # LLM fallback if available
        if self.regulated.llm:
            prompt = "You are the Cloud Healing Agent. You can: get_instance_details, resize_cloud_sql_instance, restart_instance. "
            if conv_ctx:
                prompt += f"\n\nRecent conversation:\n{conv_ctx}\n\n"
            prompt += f"The user said: {raw}. Reply with a short suggestion (e.g. 'Say \"instance cloud-sql-instance-1\" for details' or run a command). If they asked to list agents, say we support 'mesh' or 'list agents'."
            try:
                return self.conversation.record_response(self.regulated.llm.explain(prompt))
            except Exception as e:
                return self.conversation.record_response(f"I didn't understand. Try 'help'. (LLM error: {e})")
        return self.conversation.record_response(
            "I didn't understand. Try 'help', 'instance cloud-sql-instance-1', 'resize', or 'restart'."
        )
