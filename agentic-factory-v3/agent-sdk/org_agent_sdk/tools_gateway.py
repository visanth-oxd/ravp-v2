"""ToolGateway – resolve allowed tools from tool-registry and expose callables."""

import json
import os
from pathlib import Path
from typing import Any, Callable

import requests

from .errors import ToolNotAllowedError

_CONTROL_PLANE_URL = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8010")


class ToolGateway:
    """
    Resolves tool definitions from control-plane tool-registry and provides
    callable implementations.
    
    Only allows tools that are in the agent's allowed_tools list.
    Falls back to local tool implementations if registry unavailable.
    """

    def __init__(self, base_url: str | None = None, allowed_tool_names: list[str] | None = None):
        """
        Initialize tool gateway.
        
        Args:
            base_url: Control-plane base URL (defaults to CONTROL_PLANE_URL env var)
            allowed_tool_names: List of tool names this agent is allowed to use
        """
        self.base_url = (base_url or _CONTROL_PLANE_URL).rstrip("/")
        self._allowed = allowed_tool_names or []
        self._impls: dict[str, Callable[..., Any]] = {}

    def register_impl(self, name: str, fn: Callable[..., Any]) -> None:
        """
        Register a callable for tool name.
        
        Used to register tool implementations from tools/ package.
        
        Args:
            name: Tool name
            fn: Callable tool implementation
        """
        self._impls[name] = fn

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """
        Fetch tool definitions from control-plane.
        
        Returns:
            List of tool definitions, or empty list if unavailable
        """
        try:
            response = requests.get(f"{self.base_url}/tools", timeout=3)
            if response.status_code == 200:
                return response.json().get("tools", [])
        except Exception:
            pass
        return []

    def get(self, tool_name: str) -> Callable[..., Any]:
        """
        Get a tool implementation by name.
        
        Validates that tool is in allowed_tools list.
        Resolves tool implementation from tools/ package.
        
        Args:
            tool_name: Tool name to get
        
        Returns:
            Callable tool implementation
        
        Raises:
            ToolNotAllowedError: If tool not in allowed_tools
        """
        if tool_name not in self._allowed:
            raise ToolNotAllowedError(tool_name, "agent")
        
        # Check if already loaded
        if tool_name in self._impls:
            return self._impls[tool_name]
        
        # Try to load from tools package
        impl = _load_tool_impl(tool_name)
        if impl:
            self._impls[tool_name] = impl
            return impl

        # Try API-based tool from registry (tools created via UI that call existing APIs)
        impl = _resolve_api_tool(self.base_url, tool_name)
        if impl:
            self._impls[tool_name] = impl
            return impl

        # Tool not found
        raise ToolNotAllowedError(tool_name, "agent")

    def resolve_tools(self, allowed_tool_names: list[str] | None = None) -> dict[str, Callable[..., Any]]:
        """
        Resolve all allowed tools to callables.
        
        Args:
            allowed_tool_names: Optional list of allowed tools (uses self._allowed if None)
        
        Returns:
            Dict mapping tool names to callable implementations
        """
        allowed = allowed_tool_names or self._allowed
        tools = {}
        
        for name in allowed:
            try:
                tools[name] = self.get(name)
            except ToolNotAllowedError:
                # Skip tools that can't be resolved
                pass
        
        return tools

    def run(self, agent_id: str, tool_name: str, **kwargs: Any) -> Any:
        """
        Run a tool if allowed for this agent.
        
        Args:
            agent_id: Agent identifier (for error messages)
            tool_name: Tool name to run
            **kwargs: Tool arguments
        
        Returns:
            Tool result
        
        Raises:
            ToolNotAllowedError: If tool not in allowed_tools
        """
        tool = self.get(tool_name)
        return tool(**kwargs)


def _resolve_api_tool(base_url: str, tool_name: str) -> Callable[..., Any] | None:
    """
    If the tool is an API-based tool (created via UI with api_config), return a callable that executes it.
    """
    try:
        r = requests.get(f"{base_url}/tools/{tool_name}", timeout=3)
        if r.status_code != 200:
            return None
        tool_def = r.json()
        api_config = tool_def.get("api_config") if isinstance(tool_def, dict) else None
        if not api_config:
            return None
        return _make_api_executor(tool_name, tool_def)
    except Exception:
        return None


def _make_api_executor(tool_name: str, tool_def: dict[str, Any]) -> Callable[..., Any]:
    """
    Build a callable that runs an HTTP request from api_config. Callable accepts **kwargs
    that are substituted into path_template and (for GET) query, or (for POST) body.
    """
    api = tool_def.get("api_config") or {}
    method = (api.get("method") or "GET").upper()
    base_url_env = api.get("base_url_env") or ""
    path_tpl = api.get("path_template") or ""
    timeout = int(api.get("timeout_seconds") or 10)
    params_spec = api.get("parameters") or []

    def executor(**kwargs: Any) -> str:
        base_url = (os.environ.get(base_url_env) or "").rstrip("/")
        if not base_url:
            return json.dumps({"error": f"Environment variable {base_url_env!r} not set (base URL for tool {tool_name})"})
        path = path_tpl
        for p in params_spec:
            if (p.get("param_in") or "path") == "path" and p.get("name") and p["name"] in kwargs:
                path = path.replace("{" + p["name"] + "}", str(kwargs[p["name"]]))
        url = f"{base_url}{path}"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        auth_env = api.get("auth_header_env")
        if auth_env and os.environ.get(auth_env):
            headers["Authorization"] = os.environ[auth_env]
        key_header = api.get("api_key_header")
        key_env = api.get("api_key_env")
        if key_header and key_env and os.environ.get(key_env):
            headers[key_header] = os.environ[key_env]
        query_params = {p["name"]: kwargs[p["name"]] for p in params_spec if (p.get("param_in") == "query" and p.get("name") in kwargs)}
        body_data = None
        if method in ("POST", "PUT", "PATCH") and params_spec:
            body_data = {p["name"]: kwargs.get(p["name"]) for p in params_spec if (p.get("param_in") == "body" and p.get("name") in kwargs)}
            if not body_data:
                body_data = {k: v for k, v in kwargs.items() if k in [p.get("name") for p in params_spec]}
            if not body_data:
                body_data = kwargs
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, params=query_params or None, timeout=timeout)
            elif method == "POST":
                resp = requests.post(url, headers=headers, params=query_params or None, json=body_data, timeout=timeout)
            elif method == "PUT":
                resp = requests.put(url, headers=headers, params=query_params or None, json=body_data, timeout=timeout)
            elif method == "PATCH":
                resp = requests.patch(url, headers=headers, params=query_params or None, json=body_data, timeout=timeout)
            elif method == "DELETE":
                resp = requests.delete(url, headers=headers, params=query_params or None, timeout=timeout)
            else:
                return json.dumps({"error": f"Unsupported method {method}"})
            if resp.status_code >= 400:
                return json.dumps({"error": f"API returned {resp.status_code}", "body": resp.text[:500]})
            try:
                return json.dumps(resp.json())
            except Exception:
                return resp.text
        except requests.exceptions.RequestException as e:
            return json.dumps({"error": str(e)})

    return executor


def _load_tool_impl(name: str) -> Callable[..., Any] | None:
    """
    Load tool implementation from tools/ package.
    
    Requires repo root on sys.path.
    
    Args:
        name: Tool name to load
    
    Returns:
        Tool implementation callable, or None if not found
    """
    try:
        if name == "get_payment_exception":
            from tools.mcp_payment_tools import get_payment_exception
            return get_payment_exception
        if name == "suggest_payment_resolution":
            from tools.mcp_payment_tools import suggest_payment_resolution
            return suggest_payment_resolution
        if name == "get_customer_profile":
            from tools.mcp_customer_tools import get_customer_profile
            return get_customer_profile
        if name == "get_incident":
            from tools.mcp_gcp_tools import get_incident
            return get_incident
        if name == "list_incidents":
            from tools.mcp_gcp_tools import list_incidents
            return list_incidents
        if name == "request_meeting":
            from tools.mcp_coordinator_tools import request_meeting
            return request_meeting
        if name == "get_metric_series":
            from tools.mcp_gcp_tools import get_metric_series
            return get_metric_series
        if name == "get_log_entries":
            from tools.mcp_gcp_tools import get_log_entries
            return get_log_entries
        if name == "suggest_remediation":
            from tools.mcp_gcp_tools import suggest_remediation
            return suggest_remediation
        if name == "request_healing":
            from tools.mcp_gcp_tools import request_healing
            return request_healing
        if name == "get_instance_details":
            from tools.mcp_healing_tools import get_instance_details
            return get_instance_details
        if name == "resize_cloud_sql_instance":
            from tools.mcp_healing_tools import resize_cloud_sql_instance
            return resize_cloud_sql_instance
        if name == "restart_instance":
            from tools.mcp_healing_tools import restart_instance
            return restart_instance
    except ImportError:
        pass
    return None
