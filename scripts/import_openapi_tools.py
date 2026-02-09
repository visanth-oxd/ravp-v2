#!/usr/bin/env python3
"""
Import API-based tools from an OpenAPI 3.x or Swagger 2 spec.

The tool definitions are generated from the spec so you don't have to write
api_config by hand. The API's own spec describes paths, methods, and parameters.

Usage:
  python scripts/import_openapi_tools.py --spec https://api.example.com/openapi.json
  python scripts/import_openapi_tools.py --spec ./openapi.yaml --domain myapi --base-url-env MY_API_URL
  python scripts/import_openapi_tools.py --spec ./openapi.json --dry-run

Options:
  --spec       OpenAPI spec URL or file path (required)
  --domain     Domain for created tools (default: general)
  --base-url-env  Env var name for API base URL (default: from spec servers[0] or API_BASE_URL)
  --dry-run    Print what would be created without writing files
  --prefix     Optional prefix for tool IDs (e.g. myapi_)
"""

import argparse
import json
import re
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

import yaml


def load_spec(spec_ref: str) -> dict:
    """Load OpenAPI spec from URL or file. Returns parsed dict."""
    spec_ref = spec_ref.strip()
    if spec_ref.startswith(("http://", "https://")):
        try:
            import urllib.request
            with urllib.request.urlopen(spec_ref, timeout=15) as r:
                raw = r.read().decode()
        except Exception as e:
            raise SystemExit(f"Failed to fetch spec: {e}")
    else:
        path = Path(spec_ref)
        if not path.exists():
            raise SystemExit(f"File not found: {path}")
        raw = path.read_text()
    if spec_ref.endswith(".yaml") or spec_ref.endswith(".yml") or ":" in raw.split("\n")[0]:
        return yaml.safe_load(raw) or {}
    return json.loads(raw)


def slug_to_tool_id(s: str) -> str:
    """Convert operationId or path to a safe tool_id (snake_case)."""
    s = re.sub(r"[^a-zA-Z0-9/_\-]", "_", s)
    s = s.strip("_").lower()
    s = re.sub(r"_+", "_", s)
    return s or "unknown"


def get_path_params(path_str: str) -> list[str]:
    """Extract {param} names from path string."""
    return re.findall(r"\{([^}]+)\}", path_str)


def openapi_param_in_to_ours(in_val: str) -> str:
    """Map OpenAPI parameter 'in' to our param_in (path, query, body)."""
    if in_val == "path":
        return "path"
    if in_val == "query":
        return "query"
    if in_val == "body":
        return "body"
    return "query"


def generate_tools_from_spec(
    spec: dict,
    domain: str = "general",
    base_url_env: str = "API_BASE_URL",
    prefix: str = "",
) -> list[dict]:
    """
    Generate our tool definition dicts from an OpenAPI spec.
    One tool per path + method (operation).
    """
    tools = []
    paths = spec.get("paths") or {}
    # OpenAPI 3 has components; Swagger 2 might have parameters at path level
    for path_pattern, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "post", "put", "patch", "delete"):
            op = path_item.get(method)
            if not op or not isinstance(op, dict):
                continue
            operation_id = op.get("operationId") or f"{method}_{path_pattern.strip('/').replace('/', '_')}"
            tool_id = slug_to_tool_id(prefix + operation_id)
            description = (op.get("summary") or op.get("description") or f"{method.upper()} {path_pattern}").strip()[:500]

            # Build path_template: ensure path params use {name}
            path_template = path_pattern
            if not path_template.startswith("/"):
                path_template = "/" + path_template

            # Collect parameters from path, path item, and operation
            params_spec = []
            seen = set()

            # Path-level parameters
            for p in path_item.get("parameters") or []:
                if isinstance(p, dict) and p.get("name") and p["name"] not in seen:
                    seen.add(p["name"])
                    params_spec.append({
                        "name": p["name"],
                        "param_in": openapi_param_in_to_ours(p.get("in", "query")),
                        "required": p.get("required", False),
                    })
            # Operation-level parameters
            for p in op.get("parameters") or []:
                if isinstance(p, dict) and p.get("name") and p["name"] not in seen:
                    seen.add(p["name"])
                    params_spec.append({
                        "name": p["name"],
                        "param_in": openapi_param_in_to_ours(p.get("in", "query")),
                        "required": p.get("required", False),
                    })

            # OpenAPI 3 requestBody
            req_body = op.get("requestBody") or {}
            if isinstance(req_body, dict) and req_body.get("content"):
                # We don't map schema to a single param name; use a generic "body" or leave to executor
                if "body" not in seen and method in ("post", "put", "patch"):
                    params_spec.append({"name": "body", "param_in": "body", "required": req_body.get("required", False)})
                    seen.add("body")

            # Ensure path params are in params_spec
            for pname in get_path_params(path_template):
                if pname not in seen:
                    params_spec.append({"name": pname, "param_in": "path", "required": True})
                    seen.add(pname)

            tool_def = {
                "tool_id": tool_id,
                "domain": domain,
                "version": "1.0.0",
                "description": description,
                "data_sources": [spec.get("info", {}).get("title", "API") or "API"],
                "pii_level": "low",
                "risk_tier": "low",
                "requires_human_approval": False,
                "implementation_type": "api",
                "api_config": {
                    "method": method.upper(),
                    "base_url_env": base_url_env,
                    "path_template": path_template,
                    "timeout_seconds": 10,
                    "parameters": params_spec,
                },
            }
            tools.append(tool_def)
    return tools


def write_tool_to_disk(tool_def: dict, tools_base: Path, flat_tools: dict) -> None:
    """Write one tool to config/tools/{domain}/{tool_id}/1.0.0.yaml and add to flat_tools."""
    domain = tool_def["domain"]
    tool_id = tool_def["tool_id"]
    tool_dir = tools_base / domain / tool_id
    tool_dir.mkdir(parents=True, exist_ok=True)
    out = {
        "tool_id": tool_id,
        "domain": domain,
        "version": "1.0.0",
        "description": tool_def["description"],
        "data_sources": tool_def["data_sources"],
        "pii_level": tool_def["pii_level"],
        "risk_tier": tool_def["risk_tier"],
        "requires_human_approval": tool_def["requires_human_approval"],
        "implementation_type": "api",
        "api_config": tool_def["api_config"],
        "metadata": {"created_at": "import", "created_by": "import_openapi_tools"},
    }
    version_file = tool_dir / "1.0.0.yaml"
    with open(version_file, "w") as f:
        yaml.dump(out, f, default_flow_style=False, sort_keys=False)
    flat_tools[tool_id] = {
        "description": tool_def["description"],
        "data_sources": tool_def["data_sources"],
        "pii_level": tool_def["pii_level"],
        "risk_tier": tool_def["risk_tier"],
        "requires_human_approval": tool_def["requires_human_approval"],
    }


def main():
    ap = argparse.ArgumentParser(description="Import API-based tools from OpenAPI spec")
    ap.add_argument("--spec", required=True, help="OpenAPI spec URL or file path")
    ap.add_argument("--domain", default="general", help="Domain for created tools")
    ap.add_argument("--base-url-env", default="API_BASE_URL", help="Env var name for API base URL")
    ap.add_argument("--prefix", default="", help="Optional prefix for tool IDs")
    ap.add_argument("--dry-run", action="store_true", help="Only print what would be created")
    args = ap.parse_args()

    print("Loading OpenAPI spec...")
    spec = load_spec(args.spec)
    if not spec.get("paths"):
        raise SystemExit("Spec has no 'paths'; is this a valid OpenAPI spec?")
    info = spec.get("info", {})
    print(f"  Title: {info.get('title', 'N/A')}")
    print(f"  Paths: {len(spec['paths'])}")

    tools = generate_tools_from_spec(
        spec,
        domain=args.domain,
        base_url_env=args.base_url_env,
        prefix=args.prefix or "",
    )
    if not tools:
        raise SystemExit("No operations found in spec (no get/post/put/patch/delete under paths).")

    print(f"  Generated {len(tools)} tool(s):")
    for t in tools:
        print(f"    - {t['tool_id']}: {t['api_config']['method']} {t['api_config']['path_template']}")

    if args.dry_run:
        print("\nDry run: no files written. Remove --dry-run to write.")
        return 0

    tools_base = repo_root / "config" / "tools"
    tools_base.mkdir(parents=True, exist_ok=True)
    flat_tools = {}
    registry_path = repo_root / "config" / "tool_registry.yaml"
    if registry_path.exists():
        with open(registry_path) as f:
            data = yaml.safe_load(f) or {}
        flat_tools = dict(data.get("tools") or {})

    for t in tools:
        write_tool_to_disk(t, tools_base, flat_tools)

    with open(registry_path, "w") as f:
        yaml.dump({"tools": flat_tools}, f, default_flow_style=False, sort_keys=False)
    print(f"\nWrote {len(tools)} tool(s) under config/tools/{args.domain}/ and updated config/tool_registry.yaml")
    print(f"Set env: {args.base_url_env}=<your API base URL> and add tool names to agents' allowed_tools.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
