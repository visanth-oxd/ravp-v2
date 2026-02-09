# Config

The **config** folder is the main source of **static configuration** for the platform: agent definitions, tool registry, who can invoke which agent, and which user roles (personas) can see which agents. The control-plane and the Agent SDK read these files (with optional overrides from the control-plane API or environment). This README describes what each file does, how it’s used, and how it fits into the system.

---

## What’s in this folder

| Path | Purpose |
|------|--------|
| **agents/** | One YAML per agent: `config/agents/<agent_id>.yaml`. Defines identity, domain, allowed tools, policies, model, interactive default, human-in-the-loop. |
| **tool_registry.yaml** | Global list of **tool definitions** (name, description, data_sources, pii_level, risk_tier, requires_human_approval). Tools are the authority boundary: agents can only use registered tools. |
| **agent_invocation.yaml** | **Agent-to-agent invocation policy**: which agents are allowed to invoke which (e.g. only `cloud_reliability` can invoke `cloud_healing`). Enforced by the SDK’s `AgentInvocationGateway`. |
| **personas.yaml** | **Persona visibility**: which user roles (personas) can see which agents. Maps persona → list of **domains**; agents are filtered by their `domain` when the mesh API is called with `?persona=...`. |

Optional (when used):

- **tools/** – Versioned tool config can live under `config/tools/{domain}/{tool_id}/`; the control-plane tool registry loader prefers this when present.

---

## config/agents/ (agent definitions)

**What it is:** One YAML file per agent, e.g. `config/agents/payment_failed.yaml`, `config/agents/cloud_reliability.yaml`. Each file describes a single agent: who it is, what it can do, which tools and policies apply, and whether it has an LLM and interactive mode.

**Who uses it:**

- **Control-plane** – Agent Registry (file storage) reads from `config/agents/` to serve `GET /agents` and `GET /agents/{id}`. See `control-plane/agent_registry/storage/file_storage.py`.
- **Agent SDK** – When the control-plane is unavailable, `RegulatedAgent` falls back to loading `config/agents/<agent_id>.yaml` to get the definition. See `agent-sdk/org_agent_sdk/agent.py`.
- **Mesh / capabilities** – The mesh API and `agent_capabilities` can list agents and build mesh cards from these definitions (e.g. for “list agents”, persona filtering, and “when to suggest” context for LLMs).

**Main fields (see also `control-plane/agent_registry/schemas/agent-definition-v1.yaml`):**

| Field | Description |
|-------|-------------|
| `agent_id` | Unique identifier (must match filename stem and `agents/<name>/` package). |
| `version` | Semantic version (e.g. `1.0.0`). |
| `domain` | Business domain (e.g. `payments`, `cloud_platform`). Used for UI grouping and persona visibility. |
| `group` | Group for UI/persona (e.g. `business`, `cloud`, `platform`). |
| `risk_tier` | `low` \| `medium` \| `high` for governance. |
| `purpose` | `goal` (required) and optional `instructions_prefix`. |
| `allowed_tools` | List of tool names this agent may use. Must be registered in the tool registry. |
| `policies` | List of policy IDs (e.g. `payments/retry`) evaluated via the policy registry. |
| `model` | LLM model (e.g. `gemini-2.5-flash`). When set, **interactive** defaults to true. |
| `interactive` | Optional. When `model` is set, defaults to true so the agent supports interactive sessions. |
| `human_in_the_loop` | Whether high-impact actions require human approval. |
| `confidence_threshold` | Optional minimum confidence for agent decisions (0–1). |

**How it works:** At runtime, an agent is created with `RegulatedAgent(agent_id)`. The SDK (or control-plane) loads the corresponding YAML, normalizes it (e.g. default `interactive` when `model` is set), and uses it to enforce allowed tools, policy checks, audit, and LLM/interactive behaviour.

---

## config/tool_registry.yaml

**What it is:** A single YAML file that lists every **tool** that the platform knows about. Each entry has a name and metadata: description, data_sources, pii_level, risk_tier, requires_human_approval. Tools are the boundary: agents can only call tools that are both listed here and in the agent’s `allowed_tools`.

**Who uses it:**

- **Control-plane** – Tool registry loader reads `config/tool_registry.yaml` (and optionally versioned `config/tools/{domain}/{tool_id}/`) to serve `GET /tools` and admin tool APIs. See `control-plane/tool_registry/loader.py`.
- **Agent SDK** – `ToolGateway` can fetch tool definitions from the control-plane; the actual list is backed by this config (or versioned tool config).
- **UI / governance** – Manage Tools and agent creation flows use tool metadata for display and risk/PII.

**Structure:**

```yaml
tools:
  <tool_name>:
    description: "..."
    data_sources: []   # e.g. ["PaymentProcessingSystem", "TransactionEngine"]
    pii_level: none | low | medium | high
    risk_tier: low | medium | high
    requires_human_approval: true | false
```

**How it works:** When an agent’s definition lists a tool in `allowed_tools`, that tool must exist in the registry. The SDK only allows calls to tools that are in the agent’s allowed list; the registry supplies metadata for governance and UI.

---

## config/agent_invocation.yaml

**What it is:** Defines **which agents are allowed to invoke which other agents**. It is the allowlist for agent-to-agent calls (e.g. Cloud Reliability Agent invoking the Cloud Healing Agent). Invocations are enforced and audited by the SDK’s `AgentInvocationGateway`.

**Who uses it:**

- **Agent SDK** – `AgentInvocationGateway` (used by tools like `request_healing`) reads this file to decide if `caller_agent_id` is allowed to invoke `target_agent_id`. See `agent-sdk/org_agent_sdk/agent_invocation.py`.
- **Control-plane** – A2A routes and mesh may use the same policy for discovery and invoke checks.

**Structure:**

```yaml
invocation_policy:
  <target_agent_id>:    # e.g. cloud_healing
    allowed_callers:
      - <caller_agent_id>   # e.g. cloud_reliability
  # Optional per-target:
  # require_approval_for: [action1, action2]
```

**How it works:** When agent A tries to invoke agent B (e.g. via the `request_healing` tool), the gateway checks that A is in `invocation_policy.B.allowed_callers`. If not, the call is rejected. All invocations are audited with caller and target agent IDs.

---

## config/personas.yaml

**What it is:** Maps **personas** (user roles, e.g. business, cloud, platform) to the list of **domains** that role is allowed to see. Used to filter which agents appear when the mesh API is called with a persona (e.g. “show only agents a business user can see”).

**Who uses it:**

- **Control-plane** – Mesh API can filter agents by `?persona=...` using this file. See `control-plane/api/routes/mesh.py`.
- **Agent SDK** – `agent_capabilities.get_agents_for_persona(persona)` reads this and filters agents by `domain`. See `agent-sdk/org_agent_sdk/agent_capabilities.py`.
- **UI** – If the app knows the current user’s persona, it can call the mesh with that persona so the user only sees allowed agents.

**Concepts:**

- **Domain** – Set on each **agent** in `config/agents/<id>.yaml` (`domain: payments`, `cloud_platform`, etc.). Used for grouping and filtering.
- **Persona** – A **user** role (e.g. `business`, `cloud`, `platform`). This file defines: “Persona X can see agents whose `domain` is in this list.”  
- **platform** with `domains: []` means “see all agents” (no domain filter).

**Structure:**

```yaml
personas:
  business:
    domains: [payments, fraud, customer_service]
  cloud:
    domains: [cloud_platform, infrastructure]
  platform:
    domains: []   # empty = see all
```

**How it works:** `GET /mesh/agents?persona=business` returns only agents whose `domain` is in the `business` list. The SDK’s `get_agents_for_persona("business")` does the same filtering from config. Persona is only applied when something explicitly calls the mesh (or capability helpers) with a persona; the main “Browse Agents” UI may use RBAC (`GET /agents`) instead of persona.

---

## How config is loaded (paths and overrides)

- **Default paths** – Control-plane and SDK resolve paths relative to the repo root (e.g. `repo_root/config/agents`, `repo_root/config/tool_registry.yaml`). The SDK also tries the current working directory and walking up from `__file__` for `config/agents`.
- **CONFIG_DIR** – Some loaders (e.g. agent registry storage, tool registry) support a `CONFIG_DIR` environment variable to point at a config directory (e.g. `config/agents`); they then resolve sibling files (e.g. `tool_registry.yaml`) from that.
- **Control-plane as source of truth** – At runtime, the control-plane may serve agent and tool data from its own storage (which can be populated from these files or via admin APIs). The SDK prefers the control-plane and falls back to file-based config when the API is unavailable.
- **Deployments / Docker** – Deployment and Docker build flows often copy the whole `config/` tree into the image so agents and the control-plane have the same definitions in production.

---

## Summary table

| Config | Consumed by | Purpose |
|--------|-------------|--------|
| **config/agents/*.yaml** | Control-plane Agent Registry, Agent SDK (fallback), mesh/capabilities | Agent identity, domain, allowed_tools, policies, model, interactive default, human_in_the_loop. |
| **config/tool_registry.yaml** | Control-plane tool registry, ToolGateway (via API) | Global tool definitions; agents can only use tools in registry and in their allowed_tools. |
| **config/agent_invocation.yaml** | AgentInvocationGateway (SDK), A2A/mesh | Allowlist: which agent can invoke which (agent-to-agent). |
| **config/personas.yaml** | Mesh API, agent_capabilities (SDK) | Persona → domains; filter which agents a user role can see. |

Together, these files define **what agents exist**, **what they can do** (tools and policies), **who can call whom** (invocation policy), and **who can see what** (personas and domains).
