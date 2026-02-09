"""
MCP-style customer tools.

Tools for accessing customer profile data.
Authority boundary: only these modules talk to customer data.
"""

from .get_customer_profile import get_customer_profile

__all__ = ["get_customer_profile"]
