"""
Request a healing action via the Agent Invocation Gateway (agent-to-agent, secure).

The Cloud Reliability Agent does NOT have healing tools. It can only call the
Cloud Healing Agent through this gateway. The gateway enforces invocation policy
(config/agent_invocation.yaml) and audits all requests. The Healing Agent runs
with its own (elevated) permissions.
"""

import sys
import json
from pathlib import Path


def request_healing(
    caller_agent_id: str,
    action: str,
    target_id: str,
    target_type: str = "cloud_sql",
    new_tier: str | None = None,
    **kwargs,
) -> str:
    """
    Invoke the Cloud Healing Agent via the invocation gateway. Caller must be
    allowlisted in config/agent_invocation.yaml. The Reliability Agent passes
    its own agent_id as caller_agent_id so the gateway can enforce policy.

    Args:
        caller_agent_id: Agent making the request (e.g. cloud_reliability). Required.
        action: One of get_instance_details, resize_cloud_sql_instance, restart_instance
        target_id: Resource ID (e.g. cloud-sql-instance-1)
        target_type: Resource type (e.g. cloud_sql, gce_instance)
        new_tier: For resize_cloud_sql_instance, e.g. db-n1-standard-4
        **kwargs: Additional params for the healing agent

    Returns:
        JSON string result from the Healing Agent, or error if invocation denied/failed
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    agent_sdk_dir = repo_root / "agent-sdk"
    if str(agent_sdk_dir) not in sys.path:
        sys.path.insert(0, str(agent_sdk_dir))

    try:
        from org_agent_sdk.agent_invocation import AgentInvocationGateway
    except ImportError as e:
        return json.dumps({
            "error": f"Invocation gateway unavailable: {e}",
            "action": action,
            "target_id": target_id,
        })

    params = dict(kwargs)
    if new_tier is not None:
        params["new_tier"] = new_tier

    gateway = AgentInvocationGateway()
    return gateway.invoke(
        caller_agent_id=caller_agent_id,
        target_agent_id="cloud_healing",
        action=action,
        target_type=target_type,
        target_id=target_id,
        params=params,
    )
