"""Payment Failed Agent - Explains payment failures and suggests resolutions."""

__all__ = ["PaymentFailedAgent", "create_agent"]


def __getattr__(name: str):
    if name in ("PaymentFailedAgent", "create_agent"):
        from .agent import PaymentFailedAgent, create_agent
        return PaymentFailedAgent if name == "PaymentFailedAgent" else create_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
