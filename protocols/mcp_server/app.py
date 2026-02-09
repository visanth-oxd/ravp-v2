"""
MCP (Model Context Protocol) server for Agent Factory.

Exposes platform tools so any MCP client (Claude, Copilot, custom) can discover
and call them over the standard MCP protocol. Run from repo root:

  python -m protocols.mcp_server.app

Or with streamable HTTP (for remote clients):

  python -m protocols.mcp_server.app --transport streamable-http --port 8020

Requires: pip install mcp
"""

import sys
from pathlib import Path

# Ensure repo root is on path when run as module or script
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    try:
        from fastmcp import FastMCP
    except ImportError:
        raise ImportError(
            "MCP server requires the mcp package (or fastmcp). Install with: pip install mcp"
        )

mcp = FastMCP(
    "Agent Factory Tools",
    instructions="Tools for the Agent Factory platform: payments, customers, cloud reliability, healing.",
)


# ---- Payment & customer tools (MCP-wrapped) ----
@mcp.tool()
def get_customer_profile(customer_id: str) -> str:
    """Fetch customer profile from CoreBankingSystem/CustomerDataSystem. customer_id e.g. CUST-7001."""
    from tools.mcp_customer_tools import get_customer_profile as _impl
    return _impl(customer_id)


@mcp.tool()
def get_payment_exception(exception_id: str) -> str:
    """Fetch payment/transaction exception details. exception_id e.g. EX-2025-001."""
    from tools.mcp_payment_tools import get_payment_exception as _impl
    return _impl(exception_id)


@mcp.tool()
def suggest_payment_resolution(exception_id: str) -> str:
    """Suggest resolution for a failed payment (advisory). exception_id e.g. EX-2025-001."""
    from tools.mcp_payment_tools import suggest_payment_resolution as _impl
    return _impl(exception_id)


# ---- Cloud reliability tools ----
@mcp.tool()
def get_incident(incident_id: str) -> str:
    """Fetch GCP incident/alert details. incident_id e.g. INC-GCP-2025-001."""
    from tools.mcp_gcp_tools import get_incident as _impl
    return _impl(incident_id)


@mcp.tool()
def get_metric_series(
    metric_name: str | None = None,
    resource: str | None = None,
) -> str:
    """Fetch GCP metric time series. Optional: metric_name, resource filters."""
    from tools.mcp_gcp_tools import get_metric_series as _impl
    return _impl(metric_name=metric_name, resource=resource)


@mcp.tool()
def get_log_entries(
    resource: str | None = None,
    severity: str | None = None,
    limit: int = 20,
) -> str:
    """Fetch GCP log entries. Optional: resource, severity (e.g. ERROR), limit."""
    from tools.mcp_gcp_tools import get_log_entries as _impl
    return _impl(resource=resource, severity=severity, limit=limit)


@mcp.tool()
def suggest_remediation(incident_id: str) -> str:
    """Suggest remediation steps for a cloud incident (advisory). incident_id e.g. INC-GCP-2025-001."""
    from tools.mcp_gcp_tools import suggest_remediation as _impl
    return _impl(incident_id)


# ---- Healing (read-only from MCP; actual invoke goes via A2A or gateway) ----
@mcp.tool()
def get_instance_details(instance_id: str) -> str:
    """Get Cloud SQL or GCE instance details (tier, state). instance_id e.g. cloud-sql-instance-1."""
    from tools.mcp_healing_tools import get_instance_details as _impl
    return _impl(instance_id)


def main():
    import argparse
    p = argparse.ArgumentParser(description="Run Agent Factory MCP server")
    p.add_argument("--transport", default="stdio", choices=["stdio", "streamable-http"], help="MCP transport")
    p.add_argument("--port", type=int, default=8020, help="Port for streamable-http")
    p.add_argument("--host", default="127.0.0.1", help="Host for streamable-http")
    args = p.parse_args()
    if args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
