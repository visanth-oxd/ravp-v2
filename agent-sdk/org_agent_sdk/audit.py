"""AuditClient – send tool calls and decisions to audit-store (control-plane)."""

import os
from typing import Any

import requests

from .errors import RegistryUnavailableError

_CONTROL_PLANE_URL = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8010")


class AuditClient:
    """
    Client for control-plane audit-store.
    
    Falls back to no-op if API unavailable (doesn't block agent execution).
    """

    def __init__(self, base_url: str | None = None):
        """
        Initialize audit client.
        
        Args:
            base_url: Control-plane base URL (defaults to CONTROL_PLANE_URL env var)
        """
        self.base_url = (base_url or _CONTROL_PLANE_URL).rstrip("/")
        self._available: bool | None = None

    def _check_available(self) -> bool:
        """
        Check if control-plane is available.
        
        Caches result to avoid repeated checks.
        
        Returns:
            True if control-plane is reachable, False otherwise
        """
        if self._available is not None:
            return self._available
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            self._available = response.status_code == 200
        except Exception:
            self._available = False
        
        return self._available

    def log(
        self,
        agent_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Log an audit entry.
        
        Generic logging method for any event type.
        
        Args:
            agent_id: Agent identifier
            event_type: Type of event (tool_call, policy_check, decision, etc.)
            payload: Event-specific data
        """
        if not self._check_available():
            return
        
        try:
            requests.post(
                f"{self.base_url}/audit/entries",
                json={
                    "agent_id": agent_id,
                    "event_type": event_type,
                    "payload": payload,
                },
                timeout=5,
            )
        except Exception:
            # Fail silently - don't block agent execution if audit fails
            pass

    def log_tool_call(
        self,
        agent_id: str,
        tool_name: str,
        args: dict[str, Any],
        result_summary: str = "",
        error: str | None = None,
    ) -> None:
        """
        Log a tool call to audit-store.
        
        Args:
            agent_id: Agent identifier
            tool_name: Name of the tool called
            args: Tool arguments
            result_summary: Summary of tool result (truncated to 200 chars)
            error: Error message if tool call failed
        """
        self.log(
            agent_id=agent_id,
            event_type="tool_call",
            payload={
                "tool": tool_name,
                "args_sanitized": args,
                "result_summary": result_summary[:200] if result_summary else "",
                "error": error,
            },
        )

    def log_decision(
        self,
        agent_id: str,
        decision: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Log an agent decision (e.g. suggested resolution).
        
        Args:
            agent_id: Agent identifier
            decision: Decision made by agent
            context: Additional context about the decision
        """
        self.log(
            agent_id=agent_id,
            event_type="decision",
            payload={
                "decision": decision,
                "context": context or {},
            },
        )

    def log_policy_check(
        self,
        agent_id: str,
        policy_id: str,
        input_data: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        """
        Log a policy check.
        
        Args:
            agent_id: Agent identifier
            policy_id: Policy identifier
            input_data: Policy input data
            result: Policy evaluation result
        """
        self.log(
            agent_id=agent_id,
            event_type="policy_check",
            payload={
                "policy_id": policy_id,
                "input": input_data,
                "result": result,
            },
        )
