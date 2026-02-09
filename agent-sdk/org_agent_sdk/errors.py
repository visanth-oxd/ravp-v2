"""SDK exceptions – used by RegulatedAgent and clients."""


class AgentFactoryError(Exception):
    """Base for all agent factory SDK errors."""
    pass


class AgentNotFoundError(AgentFactoryError):
    """Agent definition not found in registry."""

    def __init__(self, agent_id: str, version: str | None = None):
        self.agent_id = agent_id
        self.version = version
        message = f"Agent not found: {agent_id}"
        if version:
            message += f"@{version}"
        super().__init__(message)


class AgentDisabledError(AgentFactoryError):
    """Agent or model is disabled by kill-switch."""

    def __init__(self, kind: str, id: str):
        self.kind = kind  # "agent" or "model"
        self.id = id
        super().__init__(f"{kind} is disabled: {id}")


class PolicyDeniedError(AgentFactoryError):
    """Policy evaluation denied the action."""

    def __init__(self, policy_id: str, reason: str = ""):
        self.policy_id = policy_id
        self.reason = reason
        message = f"Policy denied: {policy_id}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)


class ToolNotAllowedError(AgentFactoryError):
    """Tool not in agent's allowed_tools."""

    def __init__(self, tool_name: str, agent_id: str):
        self.tool_name = tool_name
        self.agent_id = agent_id
        super().__init__(f"Tool not allowed for agent {agent_id}: {tool_name}")


class RegistryUnavailableError(AgentFactoryError):
    """Control-plane registry not reachable."""
    pass
