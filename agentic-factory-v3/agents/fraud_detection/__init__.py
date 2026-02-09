"""Fraud Detection Agent."""

__all__ = ["FraudDetectionAgent", "create_agent"]


def __getattr__(name: str):
    if name in ("FraudDetectionAgent", "create_agent"):
        from .agent import FraudDetectionAgent, create_agent
        return FraudDetectionAgent if name == "FraudDetectionAgent" else create_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
