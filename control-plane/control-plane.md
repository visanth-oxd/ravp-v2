# Control-Plane

The **control-plane** is the central API for **RAVP v2** (REgulated Agent Vending Platform). It hosts the agent registry, tool registry, policy registry, audit store, kill-switch, auth, admin APIs (agents, tools, policies), deployments, Docker build, mesh discovery, A2A (agent-to-agent), and models. Agents and the Platform UI talk to the control-plane to load definitions, evaluate policies, log audit entries, and check the kill-switch. Everything is governed through this single API.

---

## What’s in this folder

| Path | Purpose |
|------|--------|
| **api/** | FastAPI app and route modules. `main.py` mounts all routers; routes live in `api/routes/`. |
| **agent_registry/** | Agent definitions: load/list/save/delete, RBAC, versioning. Storage reads from `config/agents/*.yaml`. |
| **tool_registry/** | Tool definitions: load from `config/tool_registry.yaml` or versioned `config/tools/{domain}/{tool_id}/`. |
| **policy_registry/** | Rego policies: list from `policies/*.rego`, evaluate via OPA or stub. |
| **audit_store/** | Append and query audit entries (in-memory, optional file append via `AUDIT_FILE`). |
| **kill_switch/** | In-memory set of disabled agent IDs and model IDs; agents check before running. |
| **deployment_registry/** | Track agent deployments (env, image, status); storage under `config/deployments/`. |
| **docker_build/** | Build and push agent Docker images (used by deployment flow). |

---

## How it’s used

- **Agent SDK** – `RegulatedAgent` loads definitions from `GET /agents/{id}`, checks kill-switch at `GET /kill-switch/agents/{id}` and `GET /kill-switch/models/{id}`, uses `POST /policies/{id}/evaluate`, and sends audit via `POST /audit/entries`. The tool gateway can fetch `GET /tools`.
- **Platform UI** – Create/browse/deploy agents, manage tools and policies, view version history; all via control-plane endpoints (agents, admin agents/tools/policies, deployments, models).
- **Mesh / A2A** – `GET /mesh/agents` (with optional `?persona=`, `?domain=`, `?capability=`) and `GET /mesh/agents/{id}` for discovery; `/a2a` for A2A-style agent cards and invoke.

---

## How it works

1. **Startup** – From repo root you run `python run_control_plane.py`. That script adds the repo and `control-plane` to the path, loads each route module from `control-plane/api/routes/` (agents, tools, policies, audit, kill_switch, auth, admin_agents, admin_tools, admin_policies, deployments, docker_build, a2a, mesh, models), then starts the FastAPI app with uvicorn on port 8010 (or `PORT`).
2. **Routes** – Each route file defines an `APIRouter` with a prefix. `api/main.py` includes all of them and exposes `/`, `/health`.
3. **Storage** – Agent and tool data come from config files under the repo (`config/agents/`, `config/tool_registry.yaml`, optional `config/tools/`). Audit and kill-switch are in-memory (single process); set `AUDIT_FILE` to also append audit to a file.
4. **Auth** – Login at `POST /api/v2/auth/login`; demo uses email-based role (`platform_admin` for admin@platform.com). Admin routes require `Authorization: Bearer <token>` and (for some) platform_admin. RBAC for agents uses the same token and optional `X-User-Email` to filter list/get by `can_view_agent` / `can_use_agent` / `can_edit_agent`.

---

## API overview

| Prefix | Route module | Purpose |
|--------|-------------|---------|
| `/agents` | agents | List/get agent definitions with RBAC. |
| `/tools` | tools | List tools, get tool by name. |
| `/policies` | policies | List policies, `POST /policies/{id}/evaluate`. |
| `/audit` | audit | `POST /audit/entries`, `GET /audit/entries?agent_id=...&limit=...`. |
| `/kill-switch` | kill_switch | Disable/enable agents and models; get status. |
| `/api/v2/auth` | auth | Login, token; dependencies for require_auth / require_platform_admin. |
| `/api/v2/agent-definitions` | admin_agents | CRUD agent definitions, version history. |
| `/api/v2/admin/tools` | admin_tools | Admin tool registry (domains, versioned tools, migrate). |
| `/api/v2/admin/policies` | admin_policies | Admin policy registry (get/put by policy_id). |
| `/api/v2/deployments` | deployments | Record and list deployments. |
| `/api/v2/docker` | docker_build | Build and push agent images. |
| `/mesh` | mesh | `GET /mesh/agents`, `GET /mesh/agents/{id}` (filter by persona, domain, capability). |
| `/a2a` | a2a | A2A agent list, agent card, invoke (uses AgentInvocationGateway). |
| `/api/v2/models` | models | List Gemini models (Google AI when `GOOGLE_API_KEY` set). |

---

## Running the control-plane

From the **repo root**:

```bash
python run_control_plane.py
```

Defaults: `http://0.0.0.0:8010`. Override port and optional HTTPS:

```bash
PORT=8011 python run_control_plane.py
SSL_KEYFILE=key.pem SSL_CERTFILE=cert.pem python run_control_plane.py
```

Alternatively, from the `control-plane` directory (with repo root and `control-plane` on `PYTHONPATH`):

```bash
uvicorn api.main:app --reload --port 8010
```

---

## Configuration and environment

| Variable | Purpose |
|----------|--------|
| **PORT** | HTTP port (default `8010`). |
| **CONFIG_DIR** | Override config root; agent registry and tool registry resolve `config/agents` and `config/tool_registry.yaml` from this when set. |
| **POLICIES_DIR** | Directory for Rego files (default `repo_root/policies`). |
| **AUDIT_FILE** | If set, audit entries are appended to this file in addition to in-memory store. |
| **GOOGLE_API_KEY** | Used by `/api/v2/models` to list Gemini models from Google AI; optional. |
| **SSL_KEYFILE** / **SSL_CERTFILE** | If both set, `run_control_plane.py` serves HTTPS. |

Agent definitions are stored under **config/agents/** (see [config/README.md](../config/README.md)). The control-plane agent registry reads from there; admin agent-definitions API writes back to the same files.

---

## Main components in brief

- **agent_registry** – `load_agent`, `list_agents`, `save_agent`, `delete_agent`, `get_version_history` (file storage). RBAC in `rbac.py` (can_view_agent, can_use_agent, can_edit_agent, can_delete_agent). Schema: `schemas/agent-definition-v1.yaml`. When LLM is set, `interactive` defaults to true in loaded definitions.
- **tool_registry** – Load from `config/tool_registry.yaml` or versioned `config/tools/{domain}/{tool_id}/`; list/get tools; admin supports domains and versioning.
- **policy_registry** – Scan `policies/**/*.rego` for policy IDs; evaluate with OPA or stub; returns `{allowed, reason, details}`.
- **audit_store** – Append entries (agent_id, event_type, payload); in-memory cap (e.g. 10k); optional file append; query by agent_id and limit.
- **kill_switch** – In-memory disabled sets for agents and models; enable/disable endpoints; agents and SDK check before run.
- **deployment_registry** – Store/list deployments by environment; YAML under `config/deployments/{env}/{agent_id}.yaml`.
- **docker_build** – Build agent images (Dockerfile template, copy config); used by deployment and scripts.
- **mesh** – Uses SDK `agent_capabilities`: list agents from config, filter by persona (config/personas.yaml), domain, or capability; get mesh card per agent.
- **a2a** – Uses `config/agent_invocation.yaml` and `AgentInvocationGateway` for A2A discovery and invoke.

---

## Example requests

```bash
# Health
curl http://localhost:8010/health

# List agents (RBAC-filtered)
curl -H "Authorization: Bearer <token>" http://localhost:8010/agents

# Get one agent
curl http://localhost:8010/agents/payment_failed

# List tools
curl http://localhost:8010/tools

# Evaluate policy
curl -X POST http://localhost:8010/policies/payments/retry/evaluate \
  -H "Content-Type: application/json" \
  -d '{"payment_id": "EX-1", "attempt": 2}'

# Append audit entry
curl -X POST http://localhost:8010/audit/entries \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "payment_failed", "event_type": "tool_call", "payload": {"tool": "get_payment_exception"}}'

# Kill-switch: disable agent
curl -X POST http://localhost:8010/kill-switch/agents/payment_failed/disable

# Mesh: list agents for persona
curl "http://localhost:8010/mesh/agents?persona=business"

# Login (demo)
curl -X POST http://localhost:8010/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@platform.com", "password": "demo"}'
```

---

## Summary

| Concept | Location | Role |
|--------|----------|------|
| API entry | `api/main.py` | FastAPI app; mounts all routers; `/`, `/health`. |
| Routes | `api/routes/*.py` | Agents, tools, policies, audit, kill_switch, auth, admin_agents, admin_tools, admin_policies, deployments, docker_build, a2a, mesh, models. |
| Agent definitions | `agent_registry/` + `config/agents/` | Load/list/save/delete; RBAC; version history; schema. |
| Tool definitions | `tool_registry/` + `config/tool_registry.yaml` | List/get; admin versioned by domain. |
| Policies | `policy_registry/` + `policies/` | List Rego; evaluate. |
| Audit | `audit_store/` | Append/query; in-memory + optional file. |
| Kill-switch | `kill_switch/` | Disable/enable agents and models. |
| Deployments | `deployment_registry/` | Record/list deployments. |
| Run script | Repo root `run_control_plane.py` | Loads route modules and starts uvicorn on port 8010. |

The control-plane is the single place the platform and agents use for registry, policy, audit, and control.
