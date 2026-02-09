"""
Agent Client - for agent-to-agent interaction.

Allows agents to discover and invoke other agents.
"""

import os
import requests
from typing import Any, Dict

_CONTROL_PLANE_URL = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8010")


class AgentClient:
    """
    Client for invoking other agents.
    
    Allows agents to interact with each other through the control-plane.
    """

    def __init__(self, base_url: str | None = None):
        """
        Initialize agent client.
        
        Args:
            base_url: Control-plane base URL (defaults to CONTROL_PLANE_URL env var)
        """
        self.base_url = (base_url or _CONTROL_PLANE_URL).rstrip("/")
        self._available: bool | None = None

    def _check_available(self) -> bool:
        """Check if control-plane is available."""
        if self._available is not None:
            return self._available
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            self._available = response.status_code == 200
        except Exception:
            self._available = False
        
        return self._available

    def list_agents(self) -> list[Dict[str, Any]]:
        """
        List all available agents.
        
        Returns:
            List of agent definitions
        """
        if not self._check_available():
            return []
        
        try:
            response = requests.get(f"{self.base_url}/agents", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception:
            return []

    def get_agent(self, agent_id: str) -> Dict[str, Any] | None:
        """
        Get agent definition.
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Agent definition or None
        """
        if not self._check_available():
            return None
        
        try:
            response = requests.get(f"{self.base_url}/agents/{agent_id}", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    # ---- Mesh API (discovery and mesh card) ----
    def list_mesh_agents(
        self,
        capability: str | None = None,
        domain: str | None = None,
        group: str | None = None,
        persona: str | None = None,
    ) -> list[Dict[str, Any]]:
        """
        List all agents in the mesh. Optionally filter by capability, domain, or persona.
        Requires control-plane to be running with mesh API.
        
        Args:
            capability: Optional capability filter (e.g. "healing", "resize_cloud_sql")
            domain: Optional domain filter (e.g. "payments", "cloud_platform"); used for UI grouping
            group: Optional legacy group filter (prefer domain)
            persona: Optional persona (e.g. "business", "cloud", "platform"); returns only agents visible to that persona
        
        Returns:
            List of dicts with agent_id, domain, group, purpose
        """
        if not self._check_available():
            return []
        try:
            params = []
            if capability:
                params.append(f"capability={requests.utils.quote(capability)}")
            if domain:
                params.append(f"domain={requests.utils.quote(domain)}")
            if group:
                params.append(f"group={requests.utils.quote(group)}")
            if persona:
                params.append(f"persona={requests.utils.quote(persona)}")
            url = f"{self.base_url}/mesh/agents"
            if params:
                url += "?" + "&".join(params)
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("agents", [])
        except Exception:
            return []

    def get_mesh_agent(self, agent_id: str) -> Dict[str, Any] | None:
        """
        Get full mesh card for one agent (definition, capability, invocable, allowed_callers).
        Requires control-plane to be running with mesh API.
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Mesh card dict or None
        """
        if not self._check_available():
            return None
        try:
            response = requests.get(f"{self.base_url}/mesh/agents/{agent_id}", timeout=5)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    def invoke_agent(
        self,
        agent_id: str,
        method: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Invoke an agent method.
        
        This is a placeholder - in production, you'd have an agent runtime
        that can execute agent methods. For now, we'll use direct imports.
        
        Args:
            agent_id: Agent identifier
            method: Method name to call
            **kwargs: Method arguments
        
        Returns:
            Method result
        """
        # For now, use direct import (in production, use agent runtime)
        # This allows agents to call each other directly
        
        try:
            # Import agent module dynamically
            import importlib
            module_path = f"agents.{agent_id}.agent"
            module = importlib.import_module(module_path)
            
            # Get agent class (assumes class name is {AgentId}Agent)
            class_name = "".join(word.capitalize() for word in agent_id.split("_")) + "Agent"
            agent_class = getattr(module, class_name)
            
            # Create agent instance
            agent_instance = agent_class()
            
            # Call method
            method_func = getattr(agent_instance, method)
            result = method_func(**kwargs)
            
            return {
                "status": "success",
                "agent_id": agent_id,
                "method": method,
                "result": result
            }
        except Exception as e:
            return {
                "status": "error",
                "agent_id": agent_id,
                "method": method,
                "error": str(e)
            }
