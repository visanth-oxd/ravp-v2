"""Kill-switch state: in-memory set of disabled agent_ids and optional model_ids."""

# In-memory state (single process); for multi-instance use a distributed store (Redis, etc.)
_disabled_agents: set[str] = set()
_disabled_models: set[str] = set()


def disable_agent(agent_id: str) -> None:
    """
    Disable an agent (prevent it from running).
    
    Args:
        agent_id: Agent identifier to disable
    """
    _disabled_agents.add(agent_id)


def enable_agent(agent_id: str) -> None:
    """
    Enable an agent (allow it to run).
    
    Args:
        agent_id: Agent identifier to enable
    """
    _disabled_agents.discard(agent_id)


def is_agent_disabled(agent_id: str) -> bool:
    """
    Check if an agent is disabled.
    
    Args:
        agent_id: Agent identifier to check
    
    Returns:
        True if agent is disabled, False otherwise
    """
    return agent_id in _disabled_agents


def disable_model(model_id: str) -> None:
    """
    Disable a model (prevent any agent from using it).
    
    Args:
        model_id: Model identifier to disable (e.g. "gemini-1.5-pro")
    """
    _disabled_models.add(model_id)


def enable_model(model_id: str) -> None:
    """
    Enable a model (allow agents to use it).
    
    Args:
        model_id: Model identifier to enable
    """
    _disabled_models.discard(model_id)


def is_model_disabled(model_id: str) -> bool:
    """
    Check if a model is disabled.
    
    Args:
        model_id: Model identifier to check
    
    Returns:
        True if model is disabled, False otherwise
    """
    return model_id in _disabled_models


def list_disabled() -> dict[str, list[str]]:
    """
    List all disabled agents and models.
    
    Returns:
        Dict with "agents" and "models" lists
    """
    return {
        "agents": sorted(_disabled_agents),
        "models": sorted(_disabled_models)
    }
