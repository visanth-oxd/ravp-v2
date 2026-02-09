"""Template Agent - Copy this to create a new agent.

Keep the __getattr__ lazy-import pattern when you add exports. It avoids a RuntimeWarning
when the agent is run as python -m agents.<name>.agent (e.g. in container CMD).
"""

__all__ = ["TemplateAgent", "create_agent"]


def __getattr__(name: str):
    if name in ("TemplateAgent", "create_agent"):
        from .agent import TemplateAgent, create_agent
        return TemplateAgent if name == "TemplateAgent" else create_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
