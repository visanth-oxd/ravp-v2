# Tools

The **tools** folder holds the **implementations** of every tool that agents can call. Tools are the **authority boundary**: agents do not call databases or external APIs directly; they call tools by name through the Agent SDK’s **ToolGateway**. Only tools that are (1) registered in the **tool registry** (control-plane / `config/tool_registry.yaml`) and (2) listed in an agent’s **allowed_tools** can be resolved and run. Each tool is a Python function in a package under `tools/`; agents register these functions with the gateway in `_register_tools()` so that `agent.tools.get(tool_name)` returns the right callable.

---

## What’s in this folder

Tools are grouped by domain in **MCP-style** packages (`mcp_<domain>_tools`). Each package exposes one or more callables (functions) that the gateway and agents use by **name** (e.g. `get_payment_exception`, `request_healing`).

| Package | Purpose | Tools (examples) |
|---------|--------|-------------------|
| **mcp_payment_tools** | Payment exceptions and resolution | get_payment_exception, suggest_payment_resolution, execute_payment_retry |
| **mcp_customer_tools** | Customer profile | get_customer_profile |
| **mcp_fraud_tools** | Fraud and risk | check_risk_score, flag_suspicious_account, get_transaction_history |
| **mcp_gcp_tools** | GCP reliability and healing | get_incident, get_metric_series, get_log_entries, suggest_remediation, request_healing. For real Cloud Logging/Monitoring see [docs/gcp-apis.md](../docs/gcp-apis.md). |
| **mcp_healing_tools** | Remediation actions (Cloud SQL, instances) | get_instance_details, resize_cloud_sql_instance, restart_instance |

- **request_healing** is special: it does not call GCP directly; it invokes the **Cloud Healing Agent** via the SDK’s **AgentInvocationGateway** (using `config/agent_invocation.yaml`). So one “tool” can be agent-to-agent.
- Tool implementations may read from **synthetic data** under `data/synthetic/` (e.g. payment_exceptions.json, customers.json, cloud_reliability/*.json) or, in production, call real systems (PaymentProcessingSystem, CoreBankingSystem, GCP APIs, etc.).

---

## How it’s used

- **Agent definitions** – In `config/agents/<agent_id>.yaml`, the `allowed_tools` list contains the **names** of tools that agent may use (e.g. `get_payment_exception`, `get_customer_profile`). These names must exist in the **tool registry** (`config/tool_registry.yaml` or control-plane).
- **Agent SDK** – When an agent is created, the SDK’s **ToolGateway** is initialized with that list. The agent’s `_register_tools()` imports functions from `tools.mcp_*_tools` and calls `self.regulated.tools.register_impl(tool_name, fn)`. Later, the agent calls `self.regulated.tools.get(tool_name)` to get the callable; the gateway checks that the name is in `allowed_tools` and returns the registered (or auto-loaded) implementation. Calling the tool is then a normal Python call: `result = tool(**kwargs)`.
- **Control-plane** – The tool registry serves `GET /tools` (and admin endpoints) from `config/tool_registry.yaml` (and optional versioned `config/tools/`). Metadata (description, data_sources, pii_level, risk_tier, requires_human_approval) is used for governance and UI; the actual code that runs is always in this `tools/` folder and is wired by the agent via `register_impl`.
- **MCP server** – The optional MCP server under `protocols/mcp_server/` can expose the same tool names so external MCP clients (e.g. Claude Desktop) can call them; implementations are still these Python functions.

---

## How it works

1. **Naming** – Tool **name** (e.g. `get_payment_exception`) is the key used in agent config, registry, and gateway. The implementation is a Python function in `tools/mcp_*_tools/`; the function name usually matches the tool name.
2. **Registration** – When an agent starts, it runs `_register_tools()`: it imports from `tools.mcp_payment_tools`, `tools.mcp_customer_tools`, etc., and calls `self.regulated.tools.register_impl("get_payment_exception", get_payment_exception)`. So the gateway’s internal map gets name → callable for that agent. The SDK can also **auto-load** some tools by name (see `agent-sdk/org_agent_sdk/tools_gateway.py` `_load_tool_impl`) when `get()` is called and no impl was registered yet.
3. **Resolving** – When the agent calls `self.regulated.tools.get("get_payment_exception")`, the gateway (1) checks that `get_payment_exception` is in the agent’s `allowed_tools`, (2) returns the registered impl if present, or (3) tries to load it via `_load_tool_impl` (which imports from the right `tools` subpackage). If the tool is not allowed, it raises `ToolNotAllowedError`.
4. **Execution** – The agent calls the returned function with the right arguments (e.g. `get_payment_exception(exception_id="EX-2025-001")`). The function may read files under `data/synthetic/`, call external APIs, or call another agent via the invocation gateway. The agent is responsible for auditing tool calls (e.g. `self.regulated.audit.log_tool_call(...)`).

---

## Tool registry (config)

Tools must be **registered** in the platform so that (1) only approved tools exist and (2) metadata is available for governance and UI. Registration is in **config/tool_registry.yaml** (see [config/README.md](../config/README.md)). Each entry has:

- **name** (key) – Must match the name used in agent `allowed_tools` and in `register_impl`.
- **description** – What the tool does.
- **data_sources** – Systems it touches (e.g. PaymentProcessingSystem, CoreBankingSystem).
- **pii_level** – none | low | medium | high.
- **risk_tier** – low | medium | high.
- **requires_human_approval** – boolean.

Agents can only use tools that appear both in the registry and in their `allowed_tools` list.

---

## Adding a new tool

### Option A: Create via Platform UI (API-based tools for production)

For tools that **call an existing HTTP API**, create them in **Manage Tools** in the Platform UI (admin):

1. Open **Manage Tools** and expand **Create new tool**.
2. Choose template **API-based tool (call existing API)**.
3. Fill in **Tool ID**, **Domain**, **Description**, and governance (data sources, PII, risk, human approval).
4. In **API configuration**: HTTP method, **Base URL env var** (e.g. `CUSTOMER_API_URL`), **Path template** (e.g. `/users/{customer_id}`), timeout, optional auth (Bearer env or API key header + env), and **Parameters** (comma-separated names matching path/query).
5. Click **Create tool**. The tool is stored in versioned config with `implementation_type: api` and `api_config`. No Python file is required.
6. At runtime, set the env var(s) you configured where the agent runs. The SDK resolves the tool by name; if the definition has `api_config`, a **generic API executor** runs the HTTP request. Add the tool name to agents’ **allowed_tools**.

### Option B: Code-based tool (Python)

1. **Implement** – Add a Python function in the right package under `tools/` (e.g. `tools/mcp_payment_tools/my_new_tool.py`). Export it from the package `__init__.py` and, if you want the SDK to auto-load it by name, add a branch in `agent-sdk/org_agent_sdk/tools_gateway.py`’s `_load_tool_impl`.
2. **Register** – Add an entry in `config/tool_registry.yaml` with the same **name** and metadata.
3. **Allow** – Add that name to the `allowed_tools` list of any agent that should use it.
4. **Wire in agent** – In the agent’s `_register_tools()`, import the function and call `self.regulated.tools.register_impl("my_new_tool", my_new_tool)`.

---

## Data and production

- **Synthetic data** – Many tools (payment exception, customer profile, incidents, metrics, logs) read from `data/synthetic/` for demos. Paths are resolved relative to the tool file (e.g. `Path(__file__).resolve().parent.parent.parent / "data" / "synthetic"`).
- **Production** – Replace file reads with calls to real systems (REST APIs, RPC, etc.). The tool remains the single place that talks to that system; agents still call the tool by name. If APIs are behind Apigee or another gateway, the tool implementation calls that gateway with the appropriate auth and headers.

---

## Calling real APIs (example: payment exceptions)

When you switch from synthetic data to a real API, the tool keeps the **same function signature and return contract** (e.g. JSON string) so agents do not need to change. Use environment variables for the API base URL and optional auth so you can switch per environment without code changes.

**Example: `get_payment_exception`**

- **Without API** – Reads `data/synthetic/payment_exceptions.json` (demos).
- **With API** – If `PAYMENT_EXCEPTIONS_API_URL` is set, the tool calls:
  - `GET {PAYMENT_EXCEPTIONS_API_URL}/{exception_id}`  
  with optional auth and returns the same JSON shape (or `{"error": "...", "exception_id": "..."}` on failure).

**Environment variables (pattern for API-backed tools):**

| Variable | Purpose |
|----------|---------|
| `PAYMENT_EXCEPTIONS_API_URL` | Base URL for the payment exceptions API (e.g. `https://api.yourbank.com/payment-exceptions` or Apigee proxy URL). If set, the tool uses the API; otherwise it uses synthetic data. |
| `PAYMENT_API_KEY` | Optional. Sent as `X-Api-Key` header. |
| `PAYMENT_API_HEADER` | Optional. Sent as `Authorization` header (e.g. `Bearer <token>`). |
| `PAYMENT_API_TIMEOUT` | Request timeout in seconds (default 10). |

**Implementation pattern:**

1. At the start of the tool, check for the API URL env var.
2. If set: build the request URL (e.g. `f"{base_url}/{exception_id}"`), set headers (Accept, optional Api-Key or Authorization), call `requests.get(url, headers=..., timeout=...)`.
3. Handle 404 (not found), 5xx (server error), timeouts, and non-JSON responses by returning a JSON string in the same error shape the agent expects (e.g. `{"error": "message", "exception_id": exception_id}`).
4. On 200, parse `response.json()` and return `json.dumps(data)` so the agent still receives a JSON string. If the API uses different field names (e.g. `id` instead of `exception_id`), normalise in the tool so the rest of the pipeline sees a consistent shape.
5. If the API URL is not set, fall back to reading from `data/synthetic/` so demos and tests keep working.

See `tools/mcp_payment_tools/get_payment_exception.py` for the full implementation. The same pattern can be applied to `get_customer_profile`, `get_incident`, and other tools that today use synthetic files.

---

## Sample: public API (config-only, no auth)

**get_public_post** is a sample API-based tool that calls the [JSONPlaceholder](https://jsonplaceholder.typicode.com) public API. It has no Python file; it is fully defined in config:

- **Config:** `config/tools/general/get_public_post/1.0.0.yaml` — `implementation_type: api`, `api_config` with `base_url_env: JSONPLACEHOLDER_API_URL`, `path_template: /posts/{post_id}`.
- **At runtime:** Set `JSONPLACEHOLDER_API_URL=https://jsonplaceholder.typicode.com`; the SDK’s generic executor runs `GET {base_url}/posts/{post_id}` and returns the JSON.

**Run the demo:**

```bash
# Control-plane must be running (e.g. python run_control_plane.py)
JSONPLACEHOLDER_API_URL=https://jsonplaceholder.typicode.com python scripts/demo_public_api_tool.py
```

See `config/tools/general/get_public_post/README.md` for details. To use in an agent, add `get_public_post` to `allowed_tools` and set the env var where the agent runs.

---

## Getting data from APIs without writing each endpoint by hand

If the API has an **OpenAPI 3.x or Swagger 2 spec** (URL or file), you can generate API-based tools from the spec so the tools don't need to be written manually. The spec describes paths, methods, and parameters; the import script turns each operation into a tool with `api_config` filled in.

1. **Get the spec** – Many APIs expose it at a URL (e.g. `https://api.example.com/openapi.json`) or you can save a file (e.g. `openapi.yaml`).
2. **Run the import script** – From the repo root:
   ```bash
   python3 scripts/import_openapi_tools.py --spec https://api.example.com/openapi.json \
     --domain myapi --base-url-env MY_API_URL
   ```
   Or with a local file (e.g. the sample):
   ```bash
   python3 scripts/import_openapi_tools.py --spec config/tools/openapi_sample.json \
     --domain general --base-url-env JSONPLACEHOLDER_API_URL
   ```
   Use `--dry-run` to see which tools would be created without writing files.
3. **Configure at runtime** – Set the env var (e.g. `MY_API_URL`) to the API base URL where the agent runs, and add the generated tool names to agents' `allowed_tools`.

The script creates one tool per path + method in the spec (e.g. `getpost`, `listposts`, `getuser`) and writes them under `config/tools/<domain>/` and updates `config/tool_registry.yaml`. No manual `api_config` is required; the API's own spec defines how the API is written.

---

## Summary

| Concept | Where | Role |
|--------|--------|------|
| Tool implementations | `tools/mcp_*_tools/*.py` | Python functions; agents call them by name via the gateway. |
| Tool name | Same as function name (e.g. get_payment_exception) | Used in allowed_tools, registry, register_impl, get(). |
| Tool registry | config/tool_registry.yaml + control-plane | Defines which tools exist and their metadata; agents may only use registered + allowed tools. |
| ToolGateway | Agent SDK | Holds allowed_tool_names; register_impl() wires name → callable; get(name) enforces allowed and returns callable. |
| Agent _register_tools() | agents/<name>/agent.py | Imports from tools.* and register_impl() so the gateway can resolve tools. |
| request_healing | tools/mcp_gcp_tools/request_healing.py | Agent-to-agent: calls AgentInvocationGateway to invoke Cloud Healing Agent. |

Tools are the **only** way agents access data and take actions; they live here, are registered in config and the control-plane, and are exposed to agents through the SDK’s ToolGateway.
