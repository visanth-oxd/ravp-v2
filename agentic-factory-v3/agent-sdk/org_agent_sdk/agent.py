"""
RegulatedAgent – loads definition from Agent Registry, enforces policy/tools/audit.

How teams are forced to behave correctly: one entry point that talks to control-plane.
"""

import os
from pathlib import Path
from typing import Any

import requests
import yaml

from .audit import AuditClient
from .errors import AgentDisabledError, AgentNotFoundError
from .llm_client import LLMClient  # Legacy support
from .llm_providers import create_llm_provider
from .policy import PolicyClient
from .tools_gateway import ToolGateway

_CONTROL_PLANE_URL = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8010")


class RegulatedAgent:
    """
    Agent that is defined and governed by the factory:
    - Definition from Agent Registry (control-plane or file fallback)
    - PolicyClient for policy checks
    - ToolGateway for allowed tools only
    - AuditClient for tool calls and decisions
    - Kill-switch check before run
    """

    def __init__(
        self,
        agent_id: str,
        version: str | None = None,
        context: dict[str, Any] | None = None,
        control_plane_url: str | None = None,
    ):
        """
        Initialize regulated agent.
        
        Args:
            agent_id: Agent identifier
            version: Optional version (ignored for file-based storage)
            context: Optional context dict for agent execution
            control_plane_url: Optional control-plane URL (defaults to env var)
        
        Raises:
            AgentNotFoundError: If agent definition not found
            AgentDisabledError: If agent or model is disabled
        """
        self.agent_id = agent_id
        self.version = version
        self.context = context or {}
        self.base_url = (control_plane_url or _CONTROL_PLANE_URL).rstrip("/")

        # Load agent definition
        self.definition = self._load_definition()
        if not self.definition:
            raise AgentNotFoundError(agent_id, version)

        # Check kill-switch (raises if disabled)
        self._check_kill_switch()

        # Initialize clients
        self.policy = PolicyClient(base_url=self.base_url)
        allowed_tools = self.definition.get("allowed_tools") or self.definition.get("tools", [])
        self.tools = ToolGateway(base_url=self.base_url, allowed_tool_names=allowed_tools)
        self.audit = AuditClient(base_url=self.base_url)
        
        # Initialize LLM client (if model is defined and API key available)
        model_id = self.definition.get("model") or self.definition.get("model_id")
        if model_id:
            try:
                # Get provider from definition or auto-detect
                # Default to "google" (unified API key-based provider)
                provider_name = self.definition.get("llm_provider") or "google"
                
                # Get provider-specific config
                provider_config = self.definition.get("llm_config", {})
                
                # Create provider using factory (supports multiple backends)
                self.llm = create_llm_provider(
                    model_id=model_id,
                    provider=provider_name,
                    **provider_config
                )
            except (ImportError, ValueError) as e:
                # LLM not available (missing dependency or API key)
                # Agent can still work without LLM (graceful degradation)
                self.llm = None
                print(f"Warning: LLM not available: {e}")
        else:
            self.llm = None

    def _load_definition(self) -> dict[str, Any] | None:
        """
        Load agent definition from control-plane or file fallback.
        
        Returns:
            Agent definition dict, or None if not found
        """
        # Try control-plane first
        try:
            response = requests.get(
                f"{self.base_url}/agents/{self.agent_id}",
                timeout=3
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass

        # File fallback - try multiple path resolution strategies
        # Strategy 1: From __file__ location (agent-sdk/org_agent_sdk/agent.py -> repo root)
        current_file = Path(__file__).resolve()
        repo_root = current_file.parent.parent.parent
        config_dir = repo_root / "config" / "agents"
        path = config_dir / f"{self.agent_id}.yaml"
        
        # Strategy 2: From current working directory
        if not path.exists():
            alt_repo_root = Path.cwd()
            alt_config_dir = alt_repo_root / "config" / "agents"
            alt_path = alt_config_dir / f"{self.agent_id}.yaml"
            if alt_path.exists():
                path = alt_path
        
        # Strategy 3: Search upward from __file__ for config/agents
        if not path.exists():
            current = current_file.parent
            for _ in range(5):  # Try up to 5 levels up
                candidate = current / "config" / "agents" / f"{self.agent_id}.yaml"
                if candidate.exists():
                    path = candidate
                    break
                current = current.parent
        
        if not path.exists():
            return None

        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        # Normalize to agent-definition-v1 schema
        if "tools" in data and "allowed_tools" not in data:
            data["allowed_tools"] = data["tools"]
        if "purpose" in data and isinstance(data["purpose"], str):
            data["purpose"] = {"goal": data["purpose"].strip()}
        if "version" not in data:
            data["version"] = "1.0.0"
        # When LLM is enabled (model set), interactive defaults to True so agents support interactive sessions
        if "interactive" not in data:
            model_id = data.get("model") or data.get("model_id")
            data["interactive"] = bool(model_id and str(model_id).strip())

        return data

    def _check_kill_switch(self) -> None:
        """
        Check if agent or its model is disabled by kill-switch.
        
        Raises:
            AgentDisabledError: If agent or model is disabled
        """
        # Check agent kill-switch
        try:
            response = requests.get(
                f"{self.base_url}/kill-switch/agents/{self.agent_id}",
                timeout=2
            )
            if response.status_code == 200 and response.json().get("disabled"):
                raise AgentDisabledError("agent", self.agent_id)
        except AgentDisabledError:
            raise
        except Exception:
            # If kill-switch unavailable, allow agent (don't block)
            pass

        # Check model kill-switch (resolve "auto" to concrete default)
        model_id = self.definition.get("model") or self.definition.get("model_id")
        if model_id:
            check_id = LLMClient.AUTO_MODEL_DEFAULT if (model_id.strip().lower() == "auto") else model_id
            try:
                response = requests.get(
                    f"{self.base_url}/kill-switch/models/{check_id}",
                    timeout=2
                )
                if response.status_code == 200 and response.json().get("disabled"):
                    raise AgentDisabledError("model", check_id)
            except AgentDisabledError:
                raise
            except Exception:
                # If kill-switch unavailable, allow model (don't block)
                pass

    @property
    def allowed_tools(self) -> list[str]:
        """Get list of allowed tool names."""
        return self.definition.get("allowed_tools") or self.definition.get("tools", [])

    @property
    def risk_tier(self) -> str:
        """Get agent risk tier."""
        return self.definition.get("risk_tier", "medium")

    @property
    def purpose(self) -> str:
        """Get agent purpose/goal."""
        p = self.definition.get("purpose")
        if isinstance(p, dict):
            return p.get("goal", "")
        return str(p or "")
    
    @property
    def skills(self) -> list[str]:
        """Get agent skills/capabilities."""
        return self.definition.get("skills", [])

    @property
    def interactive(self) -> bool:
        """
        Whether this agent supports interactive sessions (REPL, conversation).
        Defaults to True when LLM is enabled (model set); otherwise defaults to False.
        Can be overridden explicitly in the agent definition.
        """
        if "interactive" in self.definition:
            return bool(self.definition["interactive"])
        model_id = self.definition.get("model") or self.definition.get("model_id")
        return bool(model_id and str(model_id).strip())

    def decide(self, context: dict[str, Any] | None = None) -> str:
        """
        Optional hook: domain logic (e.g. RETRY vs ESCALATE).
        
        Override in subclass for custom decision logic.
        Default returns empty; runtime/ADK drives the actual flow.
        
        Args:
            context: Optional context for decision
        
        Returns:
            Decision string (empty by default)
        """
        return ""
