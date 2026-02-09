"""
Kill Switch - Emergency stop for agents and models.

Provides:
- disable_agent(agent_id) / enable_agent(agent_id) - Control agent execution
- disable_model(model_id) / enable_model(model_id) - Control model usage
- is_agent_disabled(agent_id) / is_model_disabled(model_id) - Check status
- list_disabled() - List all disabled agents and models
"""

from .state import (
    disable_agent,
    disable_model,
    enable_agent,
    enable_model,
    is_agent_disabled,
    is_model_disabled,
    list_disabled,
)

__all__ = [
    "disable_agent",
    "enable_agent",
    "is_agent_disabled",
    "disable_model",
    "enable_model",
    "is_model_disabled",
    "list_disabled",
]
