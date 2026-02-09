"""
Policy Registry - Policy-as-code enforcement (Rego policies).

Provides:
- list_policies() - List all registered policies
- evaluate(policy_id, input_json) - Evaluate a policy with input
"""

from .loader import evaluate, list_policies

__all__ = ["list_policies", "evaluate"]
