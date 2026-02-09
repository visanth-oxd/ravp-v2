"""Cloud Healing Agent – executes remediation actions (resize, restart)."""

__all__ = ["CloudHealingAgent"]


def __getattr__(name: str):
    if name == "CloudHealingAgent":
        from .agent import CloudHealingAgent
        return CloudHealingAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
