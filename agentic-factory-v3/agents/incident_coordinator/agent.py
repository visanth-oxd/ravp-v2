"""
Incident Coordinator Agent – find incidents, understand status, organize meetings
with humans and other agents, discuss defect resolution, and coordinate fixes.

Uses: list_incidents, get_incident, get_log_entries, suggest_remediation,
request_meeting, request_healing (with human approval).
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
from org_agent_sdk.agent_capabilities import get_invocable_agents_capabilities, get_all_agents_list

AGENT_ID = "incident_coordinator"


class IncidentCoordinatorAgent:
    """
    Incident Coordinator: find incidents, understand status, organize meetings
    (humans + agents), discuss resolution steps, and coordinate fixes via Healing Agent.
    """

    def __init__(self, control_plane_url: str | None = None):
        self.regulated = RegulatedAgent(
            agent_id=AGENT_ID,
            control_plane_url=control_plane_url,
        )
        self.agent_client = AgentClient(base_url=control_plane_url)
        self._pending_healing = None
        self.conversation = ConversationBuffer(max_messages=20)
        self._register_tools()

    def _register_tools(self):
        """Register tools for the coordinator."""
        from tools.mcp_gcp_tools import (
            list_incidents,
            get_incident,
            get_log_entries,
            get_metric_series,
            suggest_remediation,
            request_healing,
        )
        from tools.mcp_coordinator_tools import request_meeting

        self.regulated.tools.register_impl("list_incidents", list_incidents)
        self.regulated.tools.register_impl("get_incident", get_incident)
        self.regulated.tools.register_impl("get_log_entries", get_log_entries)
        self.regulated.tools.register_impl("get_metric_series", get_metric_series)
        self.regulated.tools.register_impl("suggest_remediation", suggest_remediation)
        self.regulated.tools.register_impl("request_healing", request_healing)
        self.regulated.tools.register_impl("request_meeting", request_meeting)

    def list_open_incidents(self, status: str = "open", limit: int = 20) -> dict:
        """List incidents (default: open). Returns parsed dict."""
        fn = self.regulated.tools.get("list_incidents")
        out = fn(status=status, limit=limit)
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="list_incidents",
            args={"status": status, "limit": limit},
            result_summary=out[:300],
        )
        return json.loads(out)

    def get_incident(self, incident_id: str) -> dict:
        """Fetch incident details. Returns parsed dict."""
        fn = self.regulated.tools.get("get_incident")
        out = fn(incident_id)
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="get_incident",
            args={"incident_id": incident_id},
            result_summary=out[:300],
        )
        return json.loads(out)

    def get_logs(self, resource: str | None = None, severity: str | None = None, limit: int = 20) -> dict:
        """Fetch log entries. Returns parsed dict."""
        fn = self.regulated.tools.get("get_log_entries")
        out = fn(resource=resource, severity=severity, limit=limit)
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="get_log_entries",
            args={"resource": resource, "severity": severity, "limit": limit},
            result_summary=out[:300],
        )
        return json.loads(out)

    def get_remediation(self, incident_id: str) -> dict:
        """Fetch remediation suggestions. Returns parsed dict."""
        fn = self.regulated.tools.get("suggest_remediation")
        out = fn(incident_id)
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="suggest_remediation",
            args={"incident_id": incident_id},
            result_summary=out[:300],
        )
        return json.loads(out)

    def request_meeting(self, participants: str, title: str, agenda: str | None = None, incident_id: str | None = None) -> dict:
        """Request a meeting with humans and/or agents. Returns parsed dict."""
        fn = self.regulated.tools.get("request_meeting")
        out = fn(participants=participants, title=title, agenda=agenda, incident_id=incident_id)
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="request_meeting",
            args={"participants": participants, "title": title},
            result_summary=out[:300],
        )
        return json.loads(out)

    def request_healing_action(self, action: str, target_id: str, new_tier: str | None = None) -> dict:
        """Invoke Healing Agent. Returns parsed dict."""
        fn = self.regulated.tools.get("request_healing")
        out = fn(
            caller_agent_id=self.regulated.agent_id,
            action=action,
            target_id=target_id,
            new_tier=new_tier,
        )
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="request_healing",
            args={"action": action, "target_id": target_id, "new_tier": new_tier},
            result_summary=out[:300],
        )
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return {"raw": out}

    def _answer_with_llm(self, user_input: str, data: str, conversation_context: str = "") -> str:
        """Use LLM to turn data into a clear, conversational answer."""
        if not self.regulated.llm:
            return data
        other_agents = ""
        try:
            other_agents = get_invocable_agents_capabilities(caller_agent_id=self.regulated.agent_id)
        except Exception:
            pass
        prompt = (
            "You are an Incident Coordinator helping someone manage incidents. "
            "The user asked a question and we have the following data. "
            "Answer in a clear, conversational way. Summarize status, findings, or next steps as appropriate. "
            "If the data suggests organizing a meeting or invoking the Healing Agent, mention that briefly.\n\n"
        )
        if conversation_context:
            prompt += f"Recent conversation:\n{conversation_context}\n\n"
        if other_agents:
            prompt += f"{other_agents}\n\n"
        prompt += f"User question: {user_input}\n\nData:\n{data}"
        try:
            return self.regulated.llm.explain(prompt)
        except Exception as e:
            return f"{data}\n\n(I couldn't generate a summary: {e})"

    def answer(self, user_input: str) -> str | None:
        """Handle a question or command. Returns None for quit/exit."""
        raw = user_input.strip()
        if not raw:
            return self.conversation.record_response(
                "I'm the Incident Coordinator. Try: 'list open incidents', 'status INC-GCP-2025-001', "
                "'schedule meeting', 'resolution steps for INC-GCP-2025-001', or 'help'."
            )

        self.conversation.append_user(raw)
        conv_ctx = self.conversation.context_for_llm(exclude_last=1)
        lower = raw.lower()

        if lower in ("quit", "exit", "q"):
            return None

        if lower == "help":
            help_text = (
                "Incident Coordinator – I find incidents, organize meetings, discuss resolution, and coordinate fixes.\n\n"
                "Commands:\n"
                "  list [open] incidents  – Find open (or all) incidents\n"
                "  status <incident_id>   – Understand status of an incident (e.g. INC-GCP-2025-001)\n"
                "  schedule meeting / request meeting – Organize a meeting (I'll ask for participants and title)\n"
                "  resolution steps <id> / discuss fix <id> – Get logs + remediation and discuss defect resolution\n"
                "  fix / invoke healing   – Request Healing Agent to apply a fix (requires your approval)\n"
                "  approve / yes          – Confirm pending healing action\n"
                "  cancel                 – Cancel pending healing\n"
                "  mesh / list agents     – List agents in the environment\n"
                "  help / quit            – This message / exit\n\n"
                "You can also ask in natural language, e.g.:\n"
                "  What open incidents do we have?\n"
                "  What's the status of INC-GCP-2025-001?\n"
                "  Schedule a war room for INC-GCP-2025-001 with on-call and cloud_reliability\n"
                "  What are the resolution steps? / How do we fix this?\n"
            )
            if self.regulated.llm:
                help_text += "\n(LLM enabled – I'll reason and answer in plain language.)"
            return self.conversation.record_response(help_text)

        # Human-in-the-loop: approve or cancel pending healing
        if lower in ("approve", "yes", "confirm") and self._pending_healing:
            pending = self._pending_healing
            self._pending_healing = None
            res = self.request_healing_action(
                action=pending["action"],
                target_id=pending["target_id"],
                new_tier=pending.get("new_tier"),
            )
            out = json.dumps(res, indent=2)
            return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx) if self.regulated.llm else out)
        if lower == "cancel" and self._pending_healing:
            self._pending_healing = None
            return self.conversation.record_response("Healing action cancelled.")

        # Extract incident ID if present
        incident_id_match = re.search(r"INC-GCP-\d+-\d+", raw, re.IGNORECASE)
        incident_id = incident_id_match.group(0) if incident_id_match else None

        # List (open) incidents – find incidents
        if ("list" in lower and "incident" in lower) or "open incident" in lower or "find incident" in lower:
            status_filter = "open" if "open" in lower else None
            data = self.list_open_incidents(status=status_filter or "open", limit=20)
            incidents = data.get("incidents", [])
            if not incidents:
                msg = "No open incidents found." if (status_filter or "open" in lower) else "No incidents found."
                return self.conversation.record_response(msg)
            lines = [f"Incidents (count={data.get('count', 0)}):"]
            for i in incidents:
                lines.append(f"  • {i.get('incident_id')} – {i.get('title')} | {i.get('severity')} | {i.get('status')}")
            out = "\n".join(lines)
            return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx) if self.regulated.llm else out)

        # Status of an incident – understand status
        if (incident_id and ("status" in lower or "understand" in lower or "what's the status" in lower)) or (lower.startswith("status ") and incident_id):
            data = self.get_incident(incident_id)
            if data.get("error"):
                return self.conversation.record_response(f"Error: {data['error']}")
            out = json.dumps(data, indent=2)
            return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx) if self.regulated.llm else out)

        # Organize meeting – request meeting with humans and/or agents
        if "meeting" in lower or "schedule" in lower or "war room" in lower or "organize" in lower:
            # Default participants and title; in a richer UI we'd prompt
            participants = "on-call, cloud_reliability"
            title = "Incident war room"
            if incident_id:
                title = f"{incident_id} war room"
                data_inc = self.get_incident(incident_id)
                if not data_inc.get("error"):
                    title = f"{incident_id}: {data_inc.get('title', title)}"
            # Parse simple "schedule meeting with X and Y" or "war room for INC-X with on-call"
            if " with " in raw:
                parts = raw.split(" with ", 1)
                if len(parts) > 1:
                    participants = parts[1].strip()
            data = self.request_meeting(participants=participants, title=title, incident_id=incident_id)
            out = json.dumps(data, indent=2)
            return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx) if self.regulated.llm else out)

        # Resolution steps / discuss defect resolution – logs + remediation + LLM
        resolution_id = incident_id or ("INC-GCP-2025-001" if ("resolution" in lower or "defect" in lower or "fix step" in lower or "discuss fix" in lower or "how do we fix" in lower) else None)
        if resolution_id and ("resolution" in lower or "defect" in lower or "fix step" in lower or "discuss fix" in lower or "how do we fix" in lower):
            logs_data = self.get_logs(limit=15)
            rem_data = self.get_remediation(resolution_id)
            inc_data = self.get_incident(resolution_id)
            lines = [f"Incident: {json.dumps(inc_data, indent=2)}", "", "Recent logs:", json.dumps(logs_data, indent=2), "", "Remediation suggestions:", json.dumps(rem_data, indent=2)]
            out = "\n".join(lines)
            return self.conversation.record_response(self._answer_with_llm(
                raw, out, conv_ctx
            ) if self.regulated.llm else out)

        # Fix / invoke healing – coordinate fix (with approval)
        if ("fix" in lower or "invoke healing" in lower or "apply remediation" in lower) and ("approve" not in lower and "cancel" not in lower):
            tid = incident_id or "cloud-sql-instance-1"
            self._pending_healing = {"action": "resize_cloud_sql_instance", "target_id": tid, "new_tier": "db-n1-standard-4"}
            return self.conversation.record_response(
                f"I can request the Healing Agent to **resize** Cloud SQL instance `{tid}` to reduce pressure. "
                "Type **approve** or **yes** to confirm, or **cancel** to abort."
            )

        # Mesh: list agents
        if lower in ("mesh", "list agents", "agents") or "other agents" in lower or "what agents" in lower:
            agents = self.agent_client.list_mesh_agents()
            if not agents:
                try:
                    agents = get_all_agents_list(repo_root)
                    agents = [{"agent_id": a["agent_id"], "domain": a.get("domain"), "purpose": a.get("purpose", "")} for a in agents]
                except Exception:
                    agents = []
            if not agents:
                return self.conversation.record_response("No agents in the mesh.")
            lines = ["Agents in the environment:"]
            for a in agents:
                lines.append(f"  • {a.get('agent_id')} ({a.get('domain')}): {(a.get('purpose') or '')[:60]}")
            return self.conversation.record_response("\n".join(lines))

        # Default: if we have an incident ID, show status and offer next steps
        if incident_id:
            data = self.get_incident(incident_id)
            if data.get("error"):
                return self.conversation.record_response(f"Error: {data['error']}")
            out = json.dumps(data, indent=2)
            return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx) if self.regulated.llm else out)

        return self.conversation.record_response(
            "I didn't understand that. I can list incidents, show status, schedule meetings, discuss resolution steps, and coordinate fixes. Try 'help'."
        )
