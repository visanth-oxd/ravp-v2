"""
Cloud Reliability Agent – uses RegulatedAgent and GCP-style tools.

This agent:
- Loads definition from Agent Registry (config/agents/cloud_reliability.yaml)
- Uses only allowed tools via ToolGateway (get_incident, get_metric_series, get_log_entries, suggest_remediation)
- Can optionally use LLM for reasoning; demo works with synthetic data and suggest_remediation tool only
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

AGENT_ID = "cloud_reliability"


class CloudReliabilityAgent:
    """
    Cloud Reliability Agent for GCP: investigate incidents using monitoring and logging.
    All actions are governed by the factory (tools, audit).
    Healing actions require explicit human approval before invocation.
    """

    def __init__(self, control_plane_url: str | None = None):
        self.regulated = RegulatedAgent(
            agent_id=AGENT_ID,
            control_plane_url=control_plane_url,
        )
        self.agent_client = AgentClient(base_url=control_plane_url)
        self._pending_healing = None  # {action, target_id, new_tier?} when waiting for approval
        self.conversation = ConversationBuffer(max_messages=20)  # bounded history for LLM context
        self._register_tools()

    def _register_tools(self):
        """Register GCP tool implementations with ToolGateway."""
        # Import tools from the tools package (which must be in PYTHONPATH)
        # The tools/ directory is copied to /app/tools/ in the Docker image
        # and /app is in PYTHONPATH.
        try:
            from tools.mcp_gcp_tools.get_incident import get_incident
            from tools.mcp_gcp_tools.get_metric_series import get_metric_series
            from tools.mcp_gcp_tools.get_log_entries import get_log_entries
            from tools.mcp_gcp_tools.suggest_remediation import suggest_remediation
            from tools.mcp_gcp_tools.request_healing import request_healing
        except ImportError:
            # Fallback for local testing if paths differ
            try:
                from tools.mcp_gcp_tools import (
                    get_incident,
                    get_metric_series,
                    get_log_entries,
                    suggest_remediation,
                    request_healing,
                )
            except ImportError:
                print("Warning: Could not import tools.mcp_gcp_tools. Tools will not work.")
                return

        self.regulated.tools.register_impl("get_incident", get_incident)
        self.regulated.tools.register_impl("get_metric_series", get_metric_series)
        self.regulated.tools.register_impl("get_log_entries", get_log_entries)
        self.regulated.tools.register_impl("suggest_remediation", suggest_remediation)
        self.regulated.tools.register_impl("request_healing", request_healing)

    def request_healing_action(
        self,
        action: str,
        target_id: str,
        new_tier: str | None = None,
    ) -> dict:
        """Invoke the Healing Agent via the invocation gateway (agent-to-agent). Returns parsed JSON result."""
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

    def investigate_incident(self, incident_id: str) -> dict:
        """
        Investigate a cloud reliability incident: fetch incident, metrics, logs, and remediation suggestions.

        Args:
            incident_id: Incident identifier (e.g. "INC-GCP-2025-001")

        Returns:
            Dict with incident details, metrics summary, log entries, and suggested remediation.
        """
        result = {"incident_id": incident_id, "steps": [], "remediation": None, "error": None}

        # 1. Fetch incident
        get_incident_fn = self.regulated.tools.get("get_incident")
        incident_json = get_incident_fn(incident_id)
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="get_incident",
            args={"incident_id": incident_id},
            result_summary=incident_json[:300],
        )
        incident_data = json.loads(incident_json)
        if incident_data.get("error"):
            result["error"] = incident_data["error"]
            return result
        result["incident"] = incident_data
        result["steps"].append("get_incident")

        # 2. Fetch metrics (for affected resources / time window)
        get_metrics_fn = self.regulated.tools.get("get_metric_series")
        metrics_json = get_metrics_fn()
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="get_metric_series",
            args={},
            result_summary=metrics_json[:300],
        )
        result["metrics"] = json.loads(metrics_json)
        result["steps"].append("get_metric_series")

        # 3. Fetch logs
        get_logs_fn = self.regulated.tools.get("get_log_entries")
        logs_json = get_logs_fn(limit=20)
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="get_log_entries",
            args={"limit": 20},
            result_summary=logs_json[:300],
        )
        result["logs"] = json.loads(logs_json)
        result["steps"].append("get_log_entries")

        # 4. Suggest remediation (advisory)
        suggest_fn = self.regulated.tools.get("suggest_remediation")
        remediation_json = suggest_fn(incident_id)
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="suggest_remediation",
            args={"incident_id": incident_id},
            result_summary=remediation_json[:300],
        )
        result["remediation"] = json.loads(remediation_json)
        result["steps"].append("suggest_remediation")

        return result

    def get_incident(self, incident_id: str) -> dict:
        """Fetch incident details only. Returns parsed dict."""
        fn = self.regulated.tools.get("get_incident")
        out = fn(incident_id)
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="get_incident",
            args={"incident_id": incident_id},
            result_summary=out[:300],
        )
        return json.loads(out)

    def get_metrics(self, metric_name: str | None = None, resource: str | None = None) -> dict:
        """Fetch metric time series. Returns parsed dict."""
        fn = self.regulated.tools.get("get_metric_series")
        out = fn(metric_name=metric_name, resource=resource)
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="get_metric_series",
            args={"metric_name": metric_name, "resource": resource},
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
        """Fetch remediation suggestions for an incident. Returns parsed dict."""
        fn = self.regulated.tools.get("suggest_remediation")
        out = fn(incident_id)
        self.regulated.audit.log_tool_call(
            agent_id=self.regulated.agent_id,
            tool_name="suggest_remediation",
            args={"incident_id": incident_id},
            result_summary=out[:300],
        )
        return json.loads(out)

    def _log_entry_message(self, e: dict) -> str:
        """Normalize log entry message (synthetic uses 'message'; Cloud Logging API uses 'text_payload')."""
        return e.get("message") or e.get("text_payload") or (str(e.get("json_payload")) if e.get("json_payload") else "(no message)")

    def format_investigation(self, result: dict) -> str:
        """Turn investigation result into readable text for the user."""
        if result.get("error"):
            return f"Error: {result['error']}"

        lines = []
        inc = result.get("incident", {})
        lines.append(f"Incident: {inc.get('incident_id', '')} – {inc.get('title', '')}")
        lines.append(f"Severity: {inc.get('severity')} | Status: {inc.get('status')} | Region: {inc.get('region')}")
        lines.append(f"Summary: {inc.get('summary', '')}")
        lines.append("")
        lines.append("Symptoms:")
        for s in inc.get("symptoms", []):
            lines.append(f"  • {s}")
        lines.append("")
        lines.append("Affected services: " + ", ".join(inc.get("affected_services", [])))
        lines.append("")

        metrics = result.get("metrics", {}).get("time_series", [])
        if metrics:
            lines.append("Metrics (summary):")
            for ts in metrics[:5]:
                summary = ts.get("summary", {})
                lines.append(f"  • {ts.get('metric')} ({ts.get('resource')}): {summary}")
            lines.append("")

        logs = result.get("logs", {}).get("entries", [])
        if logs:
            lines.append("Recent log entries:")
            for e in logs[:8]:
                msg = self._log_entry_message(e)
                lines.append(f"  [{e.get('severity')}] {e.get('timestamp')} {e.get('resource')}: {msg[:200]}")
            lines.append("")

        rem = result.get("remediation", {})
        if rem and not rem.get("error"):
            lines.append("Suggested remediation (advisory):")
            for s in rem.get("suggestions", []):
                lines.append(f"  [{s.get('priority')}] {s.get('action')}")
                lines.append(f"      Reason: {s.get('reason')}")
            if rem.get("note"):
                lines.append(f"  Note: {rem['note']}")

        return "\n".join(lines)

    def _get_other_agents_context(self) -> str:
        """Load capability descriptions of other agents this agent can invoke (for LLM awareness)."""
        try:
            return get_invocable_agents_capabilities(caller_agent_id=self.regulated.agent_id)
        except Exception:
            return ""

    def _answer_with_llm(self, user_input: str, data: str, conversation_context: str = "") -> str:
        """Use LLM to turn tool output into a clear, conversational answer. Injects other agents' capabilities and recent conversation so the agent can track the dialogue."""
        if not self.regulated.llm:
            return data
        other_agents = self._get_other_agents_context()
        skills_text = ", ".join(self.regulated.skills) if self.regulated.skills else "cloud reliability tasks"
        prompt = (
            f"You are {self.regulated.agent_id}.\n\n"
            f"Mission: {self.regulated.purpose}\n"
            f"Your capabilities: {skills_text}\n\n"
            "You are helping someone troubleshoot Google Cloud. "
            "The user asked a question and we have fetched the following data from monitoring/logging. "
            "Answer their question in a clear, conversational way. Summarize key findings; if they asked "
            "for root cause or next steps, highlight those. "
            "If the data suggests remediation that requires infrastructure changes (e.g. scaling Cloud SQL, restarting an instance), "
            "briefly recommend invoking the Healing Agent and what action would help (e.g. resize_cloud_sql_instance for high CPU). "
            "Keep the answer concise but complete.\n\n"
        )
        if conversation_context:
            prompt += f"Recent conversation (use for context):\n{conversation_context}\n\n"
        if other_agents:
            prompt += f"{other_agents}\n\n"
        prompt += f"Current user question: {user_input}\n\nData from systems:\n{data}"
        try:
            return self.regulated.llm.explain(prompt)
        except Exception as e:
            return f"{data}\n\n(I couldn't generate a summarized answer: {e})"

    def _recommend_next_steps(self, user_input: str, investigation_result: dict, conversation_context: str = "") -> str:
        """Use LLM to recommend next steps, including whether to invoke the Healing Agent, based on investigation data and other agents' capabilities."""
        if not self.regulated.llm:
            return self.format_investigation(investigation_result)
        data_str = self.format_investigation(investigation_result)
        other_agents = self._get_other_agents_context()
        prompt = (
            "You are a cloud reliability engineer. The user is asking for your recommendation on what to do next. "
            "Below is the current investigation (incident, metrics, logs, remediation suggestions). "
            "Also below are OTHER DEPLOYED AGENTS you can suggest invoking. When the situation clearly calls for infrastructure changes "
            "(e.g. high Cloud SQL CPU, connection exhaustion, need to scale or restart), recommend invoking the Healing Agent and specify "
            "the action and target (e.g. 'I recommend invoking the Healing Agent to resize Cloud SQL (action: resize_cloud_sql_instance, "
            "target_id: cloud-sql-instance-1, new_tier: db-n1-standard-4).'). If the user should first gather more info or the data doesn't support a change, say so. "
            "Give a short, actionable recommendation.\n\n"
        )
        if conversation_context:
            prompt += f"Recent conversation (use for context):\n{conversation_context}\n\n"
        if other_agents:
            prompt += f"{other_agents}\n\n"
        prompt += f"Current user question: {user_input}\n\nInvestigation data:\n{data_str}"
        try:
            return self.regulated.llm.explain(prompt)
        except Exception as e:
            return f"{data_str}\n\n(I couldn't generate a recommendation: {e})"

    def _llm_interpret_tool(self, user_input: str, conversation_context: str = "") -> dict | None:
        """Ask LLM to interpret the question and choose a tool or direct answer. Uses recent conversation for context."""
        if not self.regulated.llm:
            return None
        skills_text = ", ".join(self.regulated.skills) if self.regulated.skills else "cloud reliability tasks"
        prompt = (
            f"You are {self.regulated.agent_id}.\n\n"
            f"Mission: {self.regulated.purpose}\n"
            f"Your skills: {skills_text}\n\n"
            "The user asked something. Decide what to do.\n\n"
            "Available tools:\n"
            "- get_incident(incident_id) – fetch one incident by ID e.g. INC-GCP-2025-001\n"
            "- get_metric_series(metric_name?, resource?) – fetch metrics (optional filters)\n"
            "- get_log_entries(resource?, severity?, limit?) – fetch logs (optional: resource, severity like ERROR)\n"
            "- suggest_remediation(incident_id) – get remediation suggestions for an incident\n"
            "- investigate – full investigation for an incident (incident + metrics + logs + remediation)\n"
            "- request_healing – invoke the Healing Agent to perform an action. Use when the user asks to fix/resize/restart, "
            "call the healing agent, invoke healing, apply remediation, scale the database, etc. Requires: action, target_id; "
            "for resize also include new_tier (e.g. db-n1-standard-4). Actions: get_instance_details, resize_cloud_sql_instance, restart_instance. "
            "target_id is usually cloud-sql-instance-1 or backend-service-us-central1-a-001 for restart.\n\n"
            "Reply with ONLY a JSON object, no other text. Use one of:\n"
            '1. {"tool": "investigate", "incident_id": "INC-GCP-2025-001"}\n'
            '2. {"tool": "get_incident", "incident_id": "INC-GCP-2025-001"}\n'
            '3. {"tool": "get_metric_series", "metric_name": null or "latency", "resource": null}\n'
            '4. {"tool": "get_log_entries", "resource": null, "severity": null or "ERROR"}\n'
            '5. {"tool": "suggest_remediation", "incident_id": "INC-GCP-2025-001"}\n'
            '6. {"tool": "request_healing", "action": "resize_cloud_sql_instance", "target_id": "cloud-sql-instance-1", "new_tier": "db-n1-standard-4"}\n'
            '   or {"tool": "request_healing", "action": "get_instance_details", "target_id": "cloud-sql-instance-1"}\n'
            '   or {"tool": "request_healing", "action": "restart_instance", "target_id": "cloud-sql-instance-1"}\n'
            '7. {"tool": null, "answer": "your short answer"} if you can answer without tools.\n\n'
        )
        if conversation_context:
            prompt += f"Recent conversation (for context, e.g. which incident we were discussing):\n{conversation_context}\n\n"
        prompt += f"Current user question: {user_input}"
        try:
            text = self.regulated.llm.generate(prompt)
            text = text.strip()
            if "```" in text:
                for part in text.split("```"):
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{"):
                        return json.loads(part)
            if text.startswith("{"):
                return json.loads(text)
        except (json.JSONDecodeError, Exception):
            pass
        return None

    def answer(self, user_input: str) -> str | None:
        """
        Handle a question or command and return a text response.
        Returns None for quit/exit so the REPL can exit.
        Keeps a bounded conversation history so the agent can refer to earlier turns.
        """
        raw = user_input.strip()
        if not raw:
            return self.conversation.record_response(
                "Ask something: try 'investigate INC-GCP-2025-001', 'metrics', 'logs', or 'help'."
            )

        # Append current user message and get prior turns for LLM context
        self.conversation.append_user(raw)
        conv_ctx = self.conversation.context_for_llm(exclude_last=1)

        lower = raw.lower()
        if lower in ("quit", "exit", "q"):
            return None

        if lower == "help":
            help_text = (
                "Cloud Reliability Agent – I can help you investigate GCP incidents.\n\n"
                "Commands:\n"
                "  investigate <id>   – Full investigation (incident + metrics + logs + remediation)\n"
                "  incident <id>      – Show incident details only\n"
                "  metrics [name] [resource] – Show metric time series (optional filters)\n"
                "  logs [resource] [severity] – Show log entries (optional filters)\n"
                "  root cause / findings – Summarize findings and root cause from logs (for discussion)\n"
                "  suggest <id>       – Get remediation suggestions for an incident\n"
                "  mesh / list agents – List all agents in the environment (mesh discovery)\n"
                "  agent <id>         – Show mesh card for an agent\n"
                "  resize / invoke healing – Request Healing Agent (requires your approval: type 'approve' or 'yes' to confirm)\n"
                "  approve / yes      – Confirm pending healing action (human-in-the-loop)\n"
                "  cancel             – Cancel pending healing action\n"
                "  help               – This message\n"
                "  quit / exit        – End session\n\n"
                "You can also ask in natural language, e.g.:\n"
                "  What's wrong with INC-GCP-2025-001?\n"
                "  What agents are available? / List other agents\n"
                "  Invoke the healing agent (I will ask for approval before running)\n"
                "  What should I do? / Recommend next steps\n"
            )
            if self.regulated.llm:
                help_text += "\n(LLM is enabled: I'll reason over the data and answer in plain language.)"
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
            return self.conversation.record_response("Healing action cancelled. No changes were made.")

        # Mesh discovery: list agents in the environment (all agents can discover the mesh)
        if (
            lower in ("mesh", "list agents", "agents")
            or "other agents" in lower
            or "what agents" in lower
            or "which agents" in lower
            or "who can you invoke" in lower
            or "available agents" in lower
        ):
            agents = self.agent_client.list_mesh_agents()
            if not agents:
                try:
                    agents = get_all_agents_list(repo_root)
                    agents = [{"agent_id": a["agent_id"], "domain": a.get("domain"), "purpose": a.get("purpose", "")} for a in agents]
                except Exception:
                    agents = []
            if not agents:
                return self.conversation.record_response("No agents in the mesh (control-plane may be offline).")
            lines = ["Agents in the environment (mesh):"]
            for a in agents:
                pid = a.get("agent_id", "")
                domain = a.get("domain", "")
                purpose = (a.get("purpose") or "")[:70]
                lines.append(f"  • {pid} ({domain}): {purpose}")
            return self.conversation.record_response("\n".join(lines))

        # Mesh card for one agent: "agent <id>" or "card <id>"
        if lower.startswith("agent ") or lower.startswith("card "):
            parts = raw.split()
            if len(parts) >= 2:
                agent_id = parts[1]
                card = self.agent_client.get_mesh_agent(agent_id)
                if not card:
                    return self.conversation.record_response(f"Agent not found: {agent_id}")
                return self.conversation.record_response(json.dumps(card, indent=2))
            return self.conversation.record_response("Usage: agent <agent_id> or card <agent_id>")

        # Extract incident ID if present (e.g. INC-GCP-2025-001)
        incident_id_match = re.search(r"INC-GCP-\d+-\d+", raw, re.IGNORECASE)
        incident_id = incident_id_match.group(0) if incident_id_match else None

        # Full investigation: "investigate INC-...", "what's wrong with INC-...", "tell me about INC-..."
        if incident_id and (
            lower.startswith("investigate ")
            or "what's wrong" in lower
            or "what is wrong" in lower
            or "tell me about" in lower
            or ("investigate" in lower and "inc-" in lower)
        ):
            result = self.investigate_incident(incident_id)
            out = self.format_investigation(result)
            return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx) if self.regulated.llm else out)

        # Just incident details
        if incident_id and (lower.startswith("incident ") or ("incident" in lower and "inc-" in lower)):
            data = self.get_incident(incident_id)
            if data.get("error"):
                return self.conversation.record_response(f"Error: {data['error']}")
            out = json.dumps(data, indent=2)
            return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx) if self.regulated.llm else out)

        # Remediation only
        if incident_id and ("suggest" in lower or "remediation" in lower):
            data = self.get_remediation(incident_id)
            if data.get("error"):
                return self.conversation.record_response(f"Error: {data['error']}")
            lines = [f"Remediation for {incident_id} (advisory):"]
            for s in data.get("suggestions", []):
                lines.append(f"  [{s.get('priority')}] {s.get('action')}")
                lines.append(f"      {s.get('reason')}")
            if data.get("note"):
                lines.append(f"  Note: {data['note']}")
            out = "\n".join(lines)
            return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx) if self.regulated.llm else out)

        # Healing: get_instance_details is read-only (no approval); resize/restart require human approval
        sql_instance_match = re.search(r"cloud-sql-instance-\d+", raw, re.IGNORECASE)
        healing_instance_id = sql_instance_match.group(0) if sql_instance_match else "cloud-sql-instance-1"
        tier_match = re.search(r"db-n1-(standard|highmem)-\d+", raw, re.IGNORECASE)
        new_tier = tier_match.group(0) if tier_match else "db-n1-standard-4"

        # Read-only: get instance details (no approval needed)
        if ("instance" in lower and "detail" in lower) or ("get" in lower and "instance" in lower and "cloud" in lower):
            res = self.request_healing_action(action="get_instance_details", target_id=healing_instance_id)
            out = json.dumps(res, indent=2)
            return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx) if self.regulated.llm else out)

        # State-changing healing: require explicit approval (human_in_the_loop)
        def _set_pending_resize():
            self._pending_healing = {
                "action": "resize_cloud_sql_instance",
                "target_id": healing_instance_id,
                "new_tier": new_tier,
            }
            return (
                f"I can invoke the Healing Agent to **resize** Cloud SQL instance `{healing_instance_id}` to tier `{new_tier}`. "
                "This will change infrastructure (more CPU/memory). Type **approve** or **yes** to confirm, or **cancel** to abort."
            )
        def _set_pending_restart(tid: str):
            self._pending_healing = {"action": "restart_instance", "target_id": tid}
            return (
                f"I can invoke the Healing Agent to **restart** instance `{tid}`. "
                "Type **approve** or **yes** to confirm, or **cancel** to abort."
            )

        if "resize" in lower and ("cloud" in lower or "sql" in lower):
            return self.conversation.record_response(_set_pending_resize())
        if "restart" in lower and ("instance" in lower or healing_instance_id in lower or "backend" in lower):
            target = "backend-service-us-central1-a-001" if "backend" in lower else healing_instance_id
            return self.conversation.record_response(_set_pending_restart(target))
        if (
            ("apply" in lower and "heal" in lower)
            or ("request" in lower and "heal" in lower)
            or ("invoke" in lower and "heal" in lower)
            or ("call" in lower and "heal" in lower)
            or ("heal" in lower and "instance" in lower)
            or ("healing agent" in lower and ("invoke" in lower or "call" in lower or "ask" in lower or "run" in lower))
        ):
            return self.conversation.record_response(_set_pending_resize())

        # Metrics
        if "metric" in lower or lower == "metrics":
            parts = raw.split()
            metric_name = None
            resource = None
            if len(parts) > 1 and not parts[1].upper().startswith("INC-"):
                metric_name = parts[1]
            if len(parts) > 2:
                resource = parts[2]
            data = self.get_metrics(metric_name=metric_name, resource=resource)
            if "error" in data:
                return self.conversation.record_response(f"Error: {data.get('error')}")
            ts = data.get("time_series", [])
            lines = [f"Metric time series (interval: {data.get('query_interval', 'N/A')}):"]
            for s in ts:
                lines.append(f"  {s.get('metric')} | resource={s.get('resource')} | unit={s.get('unit')}")
                lines.append(f"    summary: {s.get('summary')}")
            out = "\n".join(lines) if lines else "No metrics found."
            return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx) if self.regulated.llm else out)

        # Logs
        if "log" in lower or lower == "logs":
            parts = raw.split()
            resource = parts[1] if len(parts) > 1 and not parts[1].upper().startswith("INC-") else None
            severity = parts[2] if len(parts) > 2 else None
            data = self.get_logs(resource=resource, severity=severity)
            if data.get("entries") is None and "error" in data:
                return self.conversation.record_response(f"Error: {data.get('error')}")
            entries = data.get("entries", [])
            lines = [f"Log entries (count={data.get('count', 0)}):"]
            for e in entries:
                msg = self._log_entry_message(e)
                lines.append(f"  [{e.get('severity')}] {e.get('timestamp')} {e.get('resource')}: {msg[:200]}")
            out = "\n".join(lines) if lines else "No log entries found."
            return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx) if self.regulated.llm else out)

        # Findings / root cause: fetch logs (and optionally incident) and ask LLM to summarize for discussion
        if self.regulated.llm and (
            "root cause" in lower or "findings" in lower or "what do the logs say" in lower
            or "explain the logs" in lower or "what happened" in lower and "log" in lower
            or "summarize the logs" in lower or "what caused" in lower
        ):
            severity_filter = "ERROR" if "error" in lower or "root cause" in lower else None
            log_data = self.get_logs(resource=None, severity=severity_filter, limit=25)
            entries = log_data.get("entries", [])
            log_lines = [f"[{e.get('severity')}] {e.get('timestamp')} {e.get('resource')}: {self._log_entry_message(e)}" for e in entries]
            log_text = "\n".join(log_lines) if log_lines else "No log entries."
            inv_id = incident_id or "INC-GCP-2025-001"
            inc_data = self.get_incident(inv_id)
            inc_text = json.dumps(inc_data, indent=2) if not inc_data.get("error") else "Incident not found."
            skills_text = ", ".join(self.regulated.skills) if self.regulated.skills else "cloud reliability analysis"
            prompt = (
                f"You are {self.regulated.agent_id} with skills in {skills_text}. "
                "The user wants to discuss findings and root cause from the logs. "
                "Below are log entries and (if available) the related incident. Summarize: (1) Key findings from the logs in order of occurrence; "
                "(2) Likely root cause and how the logs support it; (3) One or two suggested next steps. "
                "Write in clear, conversational language so the user can discuss further.\n\n"
                f"Incident:\n{inc_text}\n\nLog entries:\n{log_text}"
            )
            try:
                out = self.regulated.llm.explain(prompt)
                return self.conversation.record_response(out)
            except Exception as e:
                return self.conversation.record_response(f"Logs and incident data:\n{log_text}\n\n(I couldn't generate a summary: {e})")

        # Recommend next steps: "what should I do?", "should I invoke the healing agent?", "recommend next steps"
        if self.regulated.llm and (
            "what should i do" in lower
            or "recommend" in lower and ("next step" in lower or "action" in lower)
            or "should i invoke" in lower
            or "should we invoke" in lower
            or "do you suggest" in lower and "heal" in lower
            or "what do you suggest" in lower
        ):
            # Run full investigation for default or mentioned incident, then ask LLM to recommend (including invoking other agents)
            inv_id = incident_id or "INC-GCP-2025-001"
            result = self.investigate_incident(inv_id)
            out = self._recommend_next_steps(raw, result, conv_ctx)
            return self.conversation.record_response(out)

        # Fallback: if they mentioned an incident id, run full investigation
        if incident_id:
            result = self.investigate_incident(incident_id)
            out = self.format_investigation(result)
            return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx) if self.regulated.llm else out)

        # No keyword match: use LLM to interpret and choose a tool or answer directly
        if self.regulated.llm:
            interp = self._llm_interpret_tool(raw, conv_ctx)
            if interp and interp.get("tool"):
                tool = interp.get("tool")
                tid = interp.get("incident_id")
                if tool == "investigate" and tid:
                    res = self.investigate_incident(tid)
                    out = self.format_investigation(res)
                    return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx))
                if tool == "get_incident" and tid:
                    data = self.get_incident(tid)
                    out = json.dumps(data, indent=2) if not data.get("error") else f"Error: {data['error']}"
                    return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx))
                if tool == "get_metric_series":
                    data = self.get_metrics(
                        metric_name=interp.get("metric_name"),
                        resource=interp.get("resource"),
                    )
                    out = json.dumps(data, indent=2)
                    return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx))
                if tool == "get_log_entries":
                    data = self.get_logs(
                        resource=interp.get("resource"),
                        severity=interp.get("severity"),
                    )
                    out = json.dumps(data, indent=2)
                    return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx))
                if tool == "suggest_remediation" and tid:
                    data = self.get_remediation(tid)
                    out = json.dumps(data, indent=2) if not data.get("error") else f"Error: {data['error']}"
                    return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx))
                if tool == "request_healing":
                    target_id = interp.get("target_id") or "cloud-sql-instance-1"
                    action = interp.get("action") or "get_instance_details"
                    new_tier = interp.get("new_tier")
                    # Read-only: execute immediately
                    if action == "get_instance_details":
                        res = self.request_healing_action(action=action, target_id=target_id, new_tier=new_tier)
                        out = json.dumps(res, indent=2)
                        return self.conversation.record_response(self._answer_with_llm(raw, out, conv_ctx))
                    # State-changing: require human approval
                    self._pending_healing = {"action": action, "target_id": target_id, "new_tier": new_tier}
                    return self.conversation.record_response(
                        f"I can invoke the Healing Agent to perform **{action}** on `{target_id}`. "
                        "Type **approve** or **yes** to confirm, or **cancel** to abort."
                    )
            if interp and interp.get("answer"):
                return self.conversation.record_response(interp.get("answer", "").strip())
        return self.conversation.record_response(
            "I didn't understand that. I can investigate incidents, show metrics/logs, and suggest remediation. "
            "Try: 'investigate INC-GCP-2025-001', 'metrics', 'logs', or 'help'."
        )


# ---- HTTP server (app at module level so wrapper or python -m can start it) ----
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Cloud Reliability Agent", version="1.0.0")
_agent_instance: CloudReliabilityAgent | None = None


def _get_agent() -> CloudReliabilityAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CloudReliabilityAgent()
    return _agent_instance


@app.get("/health")
def health():
    return {"status": "healthy"}


class InvokeBody(BaseModel):
    query: str = ""


@app.post("/invoke")
def invoke(body: InvokeBody):
    query = (body.query or "").strip()
    if not query:
        return {"response": "", "error": "query required"}
    try:
        agent = _get_agent()
        out = agent.answer(query)
        return {"response": out if out is not None else ""}
    except Exception as e:
        return {"response": "", "error": str(e)}


# Start server when run as main. Fallback: when invoked as "python -m agents.cloud_reliability.agent",
# __name__ can be "agents.cloud_reliability.agent" (not "__main__") due to package import order,
# so also start if argv shows we were the -m target (fixes old images that don't use the wrapper).
def _is_main_entrypoint() -> bool:
    if __name__ == "__main__":
        return True
    # python -m agents.cloud_reliability.agent → argv is [path_or_-m, "-m", "agents.cloud_reliability.agent"] or similar
    if "-m" in sys.argv and "agents.cloud_reliability.agent" in sys.argv:
        return True
    return False


if _is_main_entrypoint():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
