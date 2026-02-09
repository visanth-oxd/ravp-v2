"""
Agent Registry - Single source of truth for agent definitions.

Provides:
- load_agent(agent_id) - Load agent definition
- list_agents() - List all registered agents
"""

from .storage.file_storage import load_agent, list_agents

__all__ = ["load_agent", "list_agents"]
