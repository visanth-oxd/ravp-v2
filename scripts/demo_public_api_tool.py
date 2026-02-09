#!/usr/bin/env python3
"""
Demo: API-based tool calling a public API (JSONPlaceholder).

Shows how a tool created via the UI (or from config) with api_config
connects to a public API at runtime. No Python implementation file needed.

Prerequisites:
  1. Control-plane running (e.g. python run_control_plane.py)
  2. Set base URL for the public API (defaults below):

     export JSONPLACEHOLDER_API_URL=https://jsonplaceholder.typicode.com
     export CONTROL_PLANE_URL=http://localhost:8010   # optional, this is the default

Run:
  cd agentic-factory-v2
  JSONPLACEHOLDER_API_URL=https://jsonplaceholder.typicode.com python scripts/demo_public_api_tool.py
"""

import json
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "agent-sdk"))

from org_agent_sdk import ToolGateway


def main():
    base_url = os.environ.get("JSONPLACEHOLDER_API_URL", "https://jsonplaceholder.typicode.com")
    control_plane = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8010").rstrip("/")

    print("Demo: API-based tool → public API (JSONPlaceholder)")
    print("=" * 60)
    print(f"  Public API base URL: {base_url}")
    print(f"  Control-plane:       {control_plane}")
    print()

    os.environ["JSONPLACEHOLDER_API_URL"] = base_url

    gateway = ToolGateway(base_url=control_plane, allowed_tool_names=["get_public_post"])

    # Resolve tool (from control-plane; has api_config → generic executor runs HTTP request)
    try:
        tool_fn = gateway.get("get_public_post")
    except Exception as e:
        print(f"  Failed to resolve tool: {e}")
        print("  Ensure control-plane is running and get_public_post is registered.")
        return 1

    print("  Calling get_public_post(post_id=1) ...")
    result = tool_fn(post_id=1)
    print()
    print("  Result (JSON):")
    try:
        data = json.loads(result)
        print(json.dumps(data, indent=2))
    except Exception:
        print(result)
    print()
    print("  Done. The agent would use this tool the same way: gateway.get('get_public_post')(post_id=1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
