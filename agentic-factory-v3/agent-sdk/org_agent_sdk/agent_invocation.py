"""
Agent Invocation Gateway – secure agent-to-agent calls.

Enforces who can invoke which agent (allowlist), audits all requests,
and runs the target agent in a separate context. The caller agent does
not get the target's tools or permissions; only the target agent executes
with its own (elevated) permissions.
"""

import importlib
import json
from pathlib import Path
from typing import Any

import yaml

from .audit import AuditClient


def _find_config_path(filename: str) -> Path | None:
    """Resolve config file (e.g. config/agent_invocation.yaml) from repo root."""
    # SDK layout: .../agentic-factory-v2/agent-sdk/org_agent_sdk/agent_invocation.py -> repo root = parent.parent.parent
    repo_root = Path(__file__).resolve().parent.parent.parent
    candidate = repo_root / "config" / filename
    if candidate.exists():
        return candidate
    if Path.cwd().joinpath("config", filename).exists():
        return Path.cwd() / "config" / filename
    return None


def _load_invocation_policy() -> dict[str, Any]:
    path = _find_config_path("agent_invocation.yaml")
    if not path:
        return {}
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
        return data.get("invocation_policy", {})
    except Exception:
        return {}


def _run_target_agent(
    target_agent_id: str,
    action: str,
    target_type: str,
    target_id: str,
    params: dict[str, Any],
    invoked_by: str,
) -> str:
    """Load and run the target agent's execute_action. Returns JSON string."""
    try:
        module_path = f"agents.{target_agent_id}.agent"
        module = importlib.import_module(module_path)
        class_name = "".join(word.capitalize() for word in target_agent_id.split("_")) + "Agent"
        agent_class = getattr(module, class_name)
        agent_instance = agent_class()
        if not hasattr(agent_instance, "execute_action"):
            return json.dumps({"error": f"Agent {target_agent_id} has no execute_action", "target_agent_id": target_agent_id})
        result = agent_instance.execute_action(
            action=action,
            target_type=target_type,
            target_id=target_id,
            params=params,
            invoked_by=invoked_by,
        )
        return result if isinstance(result, str) else json.dumps(result)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "target_agent_id": target_agent_id,
            "action": action,
        })


class AgentInvocationGateway:
    """
    Gateway for agent-to-agent invocation. Ensures:
    - Only allowlisted callers can invoke a given target agent.
    - All invocations are audited (caller request + execution result).
    - Target agent runs with its own identity/permissions (no delegation of tools to caller).
    """

    def __init__(self, audit_client: AuditClient | None = None):
        self._policy = _load_invocation_policy()
        self.audit = audit_client or AuditClient()

    def is_allowed(self, caller_agent_id: str, target_agent_id: str) -> bool:
        """Return True if caller is allowed to invoke target per config."""
        allowed = self._policy.get(target_agent_id, {}).get("allowed_callers", [])
        return caller_agent_id in allowed

    def invoke(
        self,
        caller_agent_id: str,
        target_agent_id: str,
        action: str,
        target_type: str,
        target_id: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        """
        Invoke the target agent on behalf of the caller. Enforces policy and audits.

        Args:
            caller_agent_id: Agent making the request (e.g. cloud_reliability).
            target_agent_id: Agent to run (e.g. cloud_healing).
            action: Action name (e.g. resize_cloud_sql_instance).
            target_type: Resource type (e.g. cloud_sql).
            target_id: Resource ID (e.g. cloud-sql-instance-1).
            params: Action parameters (e.g. {"new_tier": "db-n1-standard-4"}).

        Returns:
            JSON string result from the target agent, or error JSON if denied/failed.
        """
        params = params or {}

        if not self.is_allowed(caller_agent_id, target_agent_id):
            self.audit.log(
                caller_agent_id,
                "agent_invocation_denied",
                {
                    "target_agent_id": target_agent_id,
                    "action": action,
                    "target_id": target_id,
                    "reason": "caller not in allowed_callers",
                },
            )
            return json.dumps({
                "error": "Invocation not allowed",
                "reason": f"Agent {caller_agent_id} is not allowed to invoke {target_agent_id}. Check config/agent_invocation.yaml.",
                "caller_agent_id": caller_agent_id,
                "target_agent_id": target_agent_id,
            }, indent=2)

        self.audit.log(
            caller_agent_id,
            "agent_invocation_request",
            {
                "target_agent_id": target_agent_id,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "params_sanitized": params,
            },
        )

        result_json = _run_target_agent(
            target_agent_id=target_agent_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            params=params,
            invoked_by=caller_agent_id,
        )

        self.audit.log(
            caller_agent_id,
            "agent_invocation_completed",
            {
                "target_agent_id": target_agent_id,
                "action": action,
                "target_id": target_id,
                "result_summary": result_json[:300] if result_json else "",
            },
        )

        return result_json
