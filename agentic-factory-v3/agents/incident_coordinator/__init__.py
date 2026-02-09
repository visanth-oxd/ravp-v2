"""Incident Coordinator Agent – find incidents, organize meetings, discuss resolution, coordinate fixes."""

__all__ = ["IncidentCoordinatorAgent"]


def __getattr__(name: str):
    if name == "IncidentCoordinatorAgent":
        from .agent import IncidentCoordinatorAgent
        return IncidentCoordinatorAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
