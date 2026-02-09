# get_public_post – sample API-based tool (public API)

This tool is a **config-only** API-based tool. It calls the [JSONPlaceholder](https://jsonplaceholder.typicode.com) public API; no auth and no Python implementation file.

## How it works

1. **Definition** – `1.0.0.yaml` has `implementation_type: api` and `api_config`:
   - `method`: GET  
   - `base_url_env`: `JSONPLACEHOLDER_API_URL`  
   - `path_template`: `/posts/{post_id}`  
   - `parameters`: `post_id` (path)

2. **Runtime** – When an agent (or the demo script) calls this tool:
   - The SDK’s **ToolGateway** fetches the tool definition from the control-plane.
   - It sees `api_config` and builds a **generic executor** that runs the HTTP request.
   - The executor reads `JSONPLACEHOLDER_API_URL` from the environment, substitutes `post_id` into the path, and calls `GET {base_url}/posts/{post_id}`.
   - The response body is returned as a JSON string to the agent.

3. **Environment** – Set the base URL where the agent (or demo) runs:

   ```bash
   export JSONPLACEHOLDER_API_URL=https://jsonplaceholder.typicode.com
   ```

## Try it

```bash
# From repo root, with control-plane running:
JSONPLACEHOLDER_API_URL=https://jsonplaceholder.typicode.com python scripts/demo_public_api_tool.py
```

## Use in an agent

1. Add `get_public_post` to the agent’s **allowed_tools** in its YAML (e.g. `config/agents/<agent_id>.yaml`). No change to the agent’s Python code or `_register_tools()` is needed for API-based tools.
2. Set `JSONPLACEHOLDER_API_URL` in the environment where the agent runs.
3. The agent can call the tool by name, e.g. `self.regulated.tools.get("get_public_post")(post_id=1)`.

See **[docs/consuming-a-new-tool.md](../../../docs/consuming-a-new-tool.md)** for the full “what to change in the agent” checklist (YAML vs code vs env).
