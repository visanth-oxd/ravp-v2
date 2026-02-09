#!/usr/bin/env python3
"""
Start an agent's HTTP server by importing its FastAPI app and running uvicorn.
Avoids runpy and __name__ issues that can prevent the server from starting in containers.
Usage: python scripts/run_agent_server.py <agent_id>
Example: python scripts/run_agent_server.py cloud_reliability
"""
import importlib
import sys

if len(sys.argv) < 2:
    print("Usage: python run_agent_server.py <agent_id>", file=sys.stderr)
    sys.exit(1)

agent_id = sys.argv[1]
module_name = f"agents.{agent_id}.agent"
mod = importlib.import_module(module_name)
app = getattr(mod, "app", None)
if app is None:
    print(f"Module {module_name} has no 'app' attribute", file=sys.stderr)
    sys.exit(1)

import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8080)
