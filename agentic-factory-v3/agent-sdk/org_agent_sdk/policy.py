"""PolicyClient – evaluate policies via control-plane policy-registry."""

import os
from typing import Any

import requests

from .errors import PolicyDeniedError, RegistryUnavailableError

_CONTROL_PLANE_URL = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8010")


class PolicyClient:
    """
    Client for control-plane policy-registry.
    
    Evaluates policies (e.g. Rego) before allowing actions.
    Falls back to allowing if registry unavailable (doesn't block agent execution).
    """

    def __init__(self, base_url: str | None = None):
        """
        Initialize policy client.
        
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

    def evaluate(self, policy_id: str, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Evaluate a policy with input data.
        
        Returns {"allowed": bool, "reason": str, "details": {...}}.
        Raises PolicyDeniedError if policy denies the action.
        
        Args:
            policy_id: Policy identifier (e.g. "payments/retry")
            input_data: Input data for policy evaluation
        
        Returns:
            Policy evaluation result
        
        Raises:
            PolicyDeniedError: If policy denies the action
        """
        if not self._check_available():
            # Fallback: allow if registry unavailable (don't block agent)
            return {"allowed": True, "reason": "registry_unavailable", "details": {}}
        
        try:
            response = requests.post(
                f"{self.base_url}/policies/{policy_id}/evaluate",
                json=input_data,
                timeout=5,
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("allowed", True):
                raise PolicyDeniedError(
                    policy_id,
                    result.get("reason", "Policy evaluation denied")
                )
            
            return result
        except PolicyDeniedError:
            # Re-raise policy denials
            raise
        except Exception:
            # Fallback: allow if evaluation fails (don't block agent)
            return {"allowed": True, "reason": "eval_error", "details": {}}

    def allowed(self, policy_id: str, input_data: dict[str, Any]) -> bool:
        """
        Check if policy allows the action (returns bool, no exception).
        
        Args:
            policy_id: Policy identifier
            input_data: Input data for policy evaluation
        
        Returns:
            True if allowed, False if denied
        """
        try:
            self.evaluate(policy_id, input_data)
            return True
        except PolicyDeniedError:
            return False
