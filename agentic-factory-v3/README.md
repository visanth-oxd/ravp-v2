# RAVP v2 – REgulated Agent Vending Platform (agentic-factory-v2) – Overview

This document describes the **entire functionality** of the repo: every major component and how they fit together. Separate READMEs per section can be added later for detail.

---

## 1. What This Repo Is

A **governed agent platform**: you define agents (purpose, allowed tools, policies, model), register them with a central control-plane, and run them via an SDK that enforces registry, policy, audit, and kill-switch. The platform includes a Streamlit UI for creating/browsing/deploying agents, optional MCP and A2A protocols, and tool/agent mesh discovery.

---

## 2. Control-Plane

**Location:** `control-plane/`  
**Run:** `python run_control_plane.py` (from repo root; loads routes from `control-plane/api/routes/` and starts the API on port 8010).

The control-plane is the central API that provides:

| Service | Route prefix | Purpose |
|--------|---------------|---------|
| **Agent Registry** | `/agents` | List/get agent definitions; RBAC (who can view/use/edit). |
| **Tool Registry** | `/tools` | List tool definitions agents are allowed to use. |
| **Policy Registry** | `/policies` | List policies; evaluate Rego (e.g. `POST /policies/{id}/evaluate`). |
| **Audit Store** | `/audit/entries` | Append and query audit entries (tool calls, decisions). |
| **Kill-Switch** | `/kill-switch` | Disable/enable agents or models in emergencies. |
| **Auth** | `/api/v2/auth` | Login (e.g. token for UI). |
| **Admin Agents** | `/api/v2/agent-definitions` | CRUD agent definitions (create/update/delete agents). |
| **Admin Tools** | `/api/v2/admin/tools` | Admin tool registry (domains, versioned tools). |
| **Admin Policies** | `/api/v2/admin/policies` | Admin policy registry. |
| **Deployments** | `/api/v2/deployments` | Record and list agent deployments (env, image, status). |
| **Docker Build** | `/api/v2/docker` | Build and push agent Docker images. |
| **A2A** | `/a2a` | Agent-to-agent discovery and invoke (A2A protocol). |
| **Mesh** | `/mesh/agents` | List agents (with optional filters: capability, domain, persona). |
| **Models** | `/api/v2/models` | List Gemini models (for agent model dropdown; uses Google AI when API key set). |

- **Agent definitions** are stored under the control-plane’s agent registry (file-backed or as configured). Schema: `control-plane/agent_registry/schemas/agent-definition-v1.yaml` (agent_id, version, domain, risk_tier, purpose, allowed_tools, policies, model, etc.).
- **RBAC** (`control-plane/agent_registry/rbac.py`): user from token and optional `X-User-Email`; `can_view_agent`, `can_use_agent`, `can_edit_agent` drive what the UI and API return.

---

## 3. Agent Registry (Control-Plane)

**Location:** `control-plane/agent_registry/`  
**Storage:** e.g. `agent_registry/storage/file_storage.py` (list/load agents).  
**Versioning:** `agent_registry/versioning.py` (version bumps and history for updates).

- Agents are listed and loaded by agent_id; each has a definition (YAML-shaped) with domain, risk_tier, purpose, allowed_tools, policies, model, human_in_the_loop, etc.
- **List** (for UI): `GET /agents` returns agents the user can view (RBAC), with permissions and domain/group.
- **Create/Update/Delete:** Admin API `/api/v2/agent-definitions` (POST/PUT/DELETE).

---

## 4. Tool Registry (Control-Plane)

**Location:** `control-plane/tool_registry/`  
**Config:** `config/tool_registry.yaml` and/or versioned `config/tools/{domain}/{tool_id}/`.

- Exposes tool definitions to the platform; agents are only allowed to call tools that appear in their `allowed_tools` list and in the registry.
- **List:** `GET /tools`. Admin and versioned APIs under `/api/v2/admin/tools` (by domain, versions, etc.).

---

## 5. Policy Registry (Control-Plane)

**Location:** `control-plane/policy_registry/`  
**Policies:** Rego files under `policies/` (e.g. `payments/retry.rego`, `fraud/block.rego`).

- Policies are evaluated when agents need a decision (e.g. “can we retry this payment?”). The agent SDK’s `PolicyClient` calls the control-plane to evaluate.
- **List:** `GET /policies`. **Evaluate:** `POST /policies/{policy_id}/evaluate` with input JSON.

---

## 6. Audit Store (Control-Plane)

**Location:** `control-plane/audit_store/`  
**API:** `POST /audit/entries`, `GET /audit/entries?agent_id=...&limit=...`

- Tool calls and important decisions can be sent here for compliance and debugging. The agent SDK’s `AuditClient` posts entries when the agent runs tools or records decisions.

---

## 7. Kill-Switch (Control-Plane)

**Location:** `control-plane/kill_switch/`  
**API:** `/kill-switch/agents/{id}/disable`, `/kill-switch/agents/{id}/enable`, `/kill-switch/models/{id}/disable`, etc.

- Disables agents or models in emergencies. The agent SDK checks kill-switch before running; if the agent or its model is disabled, the run is blocked.

---

## 8. Agent SDK

**Location:** `agent-sdk/org_agent_sdk/`

- **RegulatedAgent** (`agent.py`): Main entry. Loads definition from control-plane (or file fallback), checks kill-switch, has `PolicyClient`, `ToolGateway`, `AuditClient`, optional `LLMClient`. Only allows tools in the agent’s `allowed_tools`; evaluates policy when needed; can post audit entries.
- **ToolGateway** (`tools_gateway.py`): Resolves tool names to callables (from `tools/mcp_*_tools/`). Enforces allowed_tools; can fetch definitions from control-plane.
- **PolicyClient** (`policy.py`): Calls control-plane to evaluate Rego policies.
- **AuditClient** (`audit.py`): Posts audit entries to control-plane.
- **LLMClient** (`llm_client.py`): Talks to Gemini (google-genai). Model can be fixed or `"auto"` (resolved to a default). Uses `GOOGLE_API_KEY`.
- **AgentClient** (`agent_client.py`): For discovery and mesh: `list_mesh_agents(capability=..., domain=..., persona=...)`, `get_mesh_agent(agent_id)`. Calls control-plane `/mesh/agents` and `/mesh/agents/{id}`.
- **agent_capabilities** (`agent_capabilities.py`): Builds mesh view from config: `get_all_agents_list()`, `get_agent_mesh_card()`, `get_agents_for_persona(persona)` (reads `config/personas.yaml` and filters by domain), `get_agents_by_capability()`.
- **agent_invocation** (`agent_invocation.py`): Agent-to-agent invocation (who can call whom; invokes other agents via gateway).
- **Conversation** (`conversation.py`): Optional conversation buffer for interactive agents (recent messages, context for LLM).

Agents (see below) use the SDK to run: load definition, check kill-switch, call tools through the gateway, evaluate policy, audit, and optionally use the LLM.

---

## 9. Agents

**Location:** `agents/`  
**Config:** `config/agents/<agent_id>.yaml` (domain, risk_tier, purpose, allowed_tools, policies, model, etc.).

Each agent is a Python package (e.g. `agents/cloud_reliability/`, `agents/payment_failed/`) with:

- **agent.py:** Defines the agent class (subclass or uses `RegulatedAgent`), loads definition, wires tools/LLM, implements `answer()` or similar for interactive use.
- **interactive.py:** REPL or script to run the agent interactively (e.g. `python -m agents.cloud_reliability.interactive`). Supports conversation history, mesh discovery (`list agents`, `agent <id>`), and domain-specific commands (e.g. “investigate”, “approve” for healing).

**Built-in agents:** cloud_reliability, cloud_healing, fraud_detection, payment_failed, template (and others under `config/agents/`). They share: definition in YAML, allowed_tools, optional LLM, optional human-in-the-loop (e.g. approve before healing).

---

## 10. Tools (What Agents Call)

**Location:** `tools/`  
**Packages:** `mcp_payment_tools`, `mcp_customer_tools`, `mcp_gcp_tools`, `mcp_healing_tools`, `mcp_fraud_tools`, etc.

- **Tools** are Python functions (e.g. `get_payment_exception`, `get_customer_profile`, `get_incident`). The agent does not call HTTP directly; it calls a **tool by name**. The **ToolGateway** resolves the name to the implementation in `tools/`.
- Tool implementations can **call existing APIs** (e.g. REST). If your APIs are behind Apigee, the tool calls the Apigee proxy URL with the right auth headers. So: agent → tool (by name) → your code → HTTP to API/Apigee.
- Tools are registered in the control-plane tool registry and listed in each agent’s `allowed_tools`; only those are callable by that agent.

---

## 11. Config

- **config/agents/*.yaml** – Agent definitions (domain, purpose, allowed_tools, policies, model, risk_tier, human_in_the_loop). The control-plane agent registry may load from here or from its own storage.
- **config/personas.yaml** – Maps **persona** (user role) → list of **domains** that role can see. Used when you call `GET /mesh/agents?persona=business` (filter agents by domain for that persona). **Domain** = agent category (set per agent). **Persona** = user role (e.g. business, cloud, platform); persona is only applied when something explicitly calls the mesh API with `?persona=...`.
- **config/tool_registry.yaml** – Tool metadata for the platform.
- **config/agent_invocation.yaml** – Which agents can invoke which (agent-to-agent allowlist).

---

## 12. Domain and Persona

- **Domain:** Set on each **agent** in its YAML (`domain: payments`). Used to group agents in the UI (e.g. “Payments”, “Cloud Platform”) and, when using persona, to restrict which agents a user can see.
- **Persona:** A **user** role (e.g. business, cloud, platform). **personas.yaml** maps each persona to a list of domains. **Persona logic is applied only when** something calls `GET /mesh/agents?persona=<name>` (or the SDK equivalent). The Browse Agents UI currently uses `GET /agents` (RBAC), not the mesh with persona; so to enforce persona in the UI you’d need to call the mesh API with the current user’s persona and use that list.

---

## 13. Platform UI

**Location:** `platform_ui/app.py` (Streamlit).  
**Run:** `streamlit run platform_ui/app.py` (with control-plane URL, e.g. `API_URL=http://localhost:8010`).

Tabs (high level):

- **Create Agent** – Form to create a new agent (agent_id, domain, model dropdown including “Auto”, tools, policies, etc.); calls `POST /api/v2/agent-definitions`.
- **My Agents** – List agents the user can see (from `GET /agents`), with edit/deploy and version info.
- **Browse Agents** – Agents grouped by **domain** (from `GET /agents`); expanders per agent with deploy/interact/view details.
- **Deploy Agent** – Deploy flow (registry, build/push image, deployment config); uses control-plane deployment and Docker build APIs.
- **Deployed Agents** – View deployment status.
- **Manage Tools / Manage Policies** – Admin-only; manage tool and policy registries.
- **Version History** – Per-agent version history from control-plane.
- **How it works** – Diagram and short description of flow (user → control-plane → agent → tools/mesh → audit → response).

Auth: login (e.g. `POST /api/v2/auth/login`); token and optional `X-User-Email` sent to control-plane for RBAC.

---

## 14. Deployment and Docker

- **Deployments** are recorded via `POST /api/v2/deployments` (agent_id, environment, deployment_type, image_url, etc.).
- **Docker build:** Control-plane can build and push agent images (`/api/v2/docker/build-and-push`) when Docker is available. Scripts under `scripts/` (e.g. `deploy_agent.py`, `generate_deployment_manifest.py`) and `control-plane/docker_build/` support building and deploying agents.

---

## 15. MCP (Model Context Protocol)

**Location:** `protocols/mcp_server/app.py`

- Optional **MCP server** that exposes the same platform tools (e.g. get_payment_exception, get_customer_profile, get_incident) over the MCP wire protocol (stdio or streamable-http). So external MCP clients (e.g. Claude Desktop, IDEs) can call these tools without using the agent SDK. Run: `python -m protocols.mcp_server.app` (optionally `--transport streamable-http --port 8020`). Agents do not require MCP to run; they use the SDK and tool implementations directly. MCP is for interoperability with external tools-consuming apps.

---

## 16. A2A (Agent-to-Agent)

- **Control-plane** exposes A2A-style routes under `/a2a` (discovery, invoke). Agents can discover and invoke other agents (e.g. cloud_reliability → cloud_healing) according to `config/agent_invocation.yaml` and the invocation gateway in the SDK. So “agent mesh” and “A2A” are the same idea: one agent calling another via the control-plane or gateway.

---

## 17. Run and Quick Start

- **Control-plane:** From repo root, `python run_control_plane.py` (loads all route modules from `control-plane/api/routes/`, including `models`, and starts the API on port 8010).
- **UI:** Set `API_URL=http://localhost:8010` (or your control-plane URL), then `streamlit run platform_ui/app.py`.
- **Interactive agent:** e.g. `python -m agents.cloud_reliability.interactive` (ensure control-plane and any env vars like `GOOGLE_API_KEY` are set if the agent uses the LLM).

Dependencies: `pip install -r requirements.txt`. Optional: `google-genai` for LLM; `mcp` for MCP server.

---

## 18. Summary Table

| Component | Location | Role |
|-----------|----------|------|
| Control-plane API | `control-plane/api/`, `run_control_plane.py` | Registry, policy, audit, kill-switch, auth, admin, deployments, mesh, models |
| Agent registry | `control-plane/agent_registry/` | Store and serve agent definitions; RBAC |
| Tool registry | `control-plane/tool_registry/`, `config/tool_registry.yaml` | Tool catalog and versioning |
| Policy registry | `control-plane/policy_registry/`, `policies/` | Rego policies and evaluation |
| Audit store | `control-plane/audit_store/` | Append and query audit entries |
| Kill-switch | `control-plane/kill_switch/` | Disable agents or models |
| Agent SDK | `agent-sdk/org_agent_sdk/` | RegulatedAgent, ToolGateway, Policy, Audit, LLM, mesh client |
| Agents | `agents/*/`, `config/agents/*.yaml` | Agent implementations and definitions |
| Tools | `tools/mcp_*_tools/` | Tool implementations (can call APIs/Apigee) |
| Config | `config/` | agents, personas, tool_registry, agent_invocation |
| Platform UI | `platform_ui/app.py` | Create/browse/deploy agents, manage tools/policies, “How it works” |
| MCP server | `protocols/mcp_server/` | Expose tools over MCP (optional) |
| A2A | Control-plane `/a2a`, SDK invocation | Agent-to-agent discovery and invoke |

This single README is intended to cover the whole repo; you can add separate READMEs per section (e.g. control-plane, SDK, agents, UI) for deeper detail later.
