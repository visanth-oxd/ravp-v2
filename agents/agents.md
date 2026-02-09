# Agents

The **agents** folder holds **domain-specific agent implementations**. Each agent uses the [Agent SDK](../agent-sdk/README.md) (`RegulatedAgent`), loads its definition from the control-plane or `config/agents/<agent_id>.yaml`, registers only its allowed tools, and runs with policy, audit, and optional LLM. Agents can be run **programmatically** (APIs, scripts) or **interactively** (REPL via `interactive.py`).

---

## What’s in this folder

Each agent is a **Python package** under `agents/`:

| Agent | Purpose |
|-------|--------|
| **template** | Starter template; copy to create a new agent. |
| **cloud_reliability** | Investigate GCP incidents (metrics, logs), suggest remediation, optionally request healing (agent-to-agent). |
| **cloud_healing** | Execute healing actions (resize Cloud SQL, restart instance). Invoked by Cloud Reliability via the invocation gateway. |
| **payment_failed** | Explain payment failures, suggest resolutions, optional retry with policy checks and audit. |
| **fraud_detection** | Fraud detection and investigation using fraud tools and policies. |

Common layout per agent:

- **`agent.py`** – Agent class (e.g. `CloudReliabilityAgent`). Builds `RegulatedAgent(agent_id)`, registers tools with `ToolGateway`, implements `process()` and/or `answer()`.
- **`interactive.py`** – REPL entrypoint: `python -m agents.<agent>.interactive`. Prompts “You>”, calls `agent.answer(user_input)` in a loop; `answer()` returns `None` for quit.
- **`cli.py`** – Optional CLI (e.g. cloud_reliability, payment_failed) for non-interactive commands.

---

## How it’s used

### 1. Definition (config)

Each agent has a **definition** in `config/agents/<agent_id>.yaml` (or from the control-plane Agent Registry). The definition includes:

- `agent_id`, `version`, `domain`, `risk_tier`, `purpose`
- `allowed_tools` – only these tool names can be used
- `policies` – policy IDs for checks (e.g. `payments/retry`)
- `model` – LLM model (e.g. `gemini-2.5-flash`); when set, **interactive is enabled by default**
- `human_in_the_loop` – whether to require human approval for certain actions

The SDK loads this definition when you create `RegulatedAgent(agent_id)`.

### 2. Agent class (agent.py)

- **Init:** Create `RegulatedAgent(agent_id, control_plane_url=...)`. The SDK loads the definition, checks the kill-switch, and sets up `policy`, `tools`, `audit`, `llm`. Then register tool implementations with `self.regulated.tools.register_impl(name, fn)` (importing from `tools/mcp_*_tools`). Optionally create `ConversationBuffer` and `AgentClient` for mesh/interactive.
- **Process:** Implement domain methods (e.g. `investigate_incident()`, `investigate_payment_exception()`). Inside them:
  - Get tools via `self.regulated.tools.get(tool_name)` (only allowed tools succeed).
  - Call `self.regulated.policy.evaluate(policy_id, input)` when a decision needs a policy check.
  - Log with `self.regulated.audit.log()` or `log_tool_call()`.
  - Use `self.regulated.llm` for reasoning when available.
- **Answer (interactive):** Implement `answer(user_input) -> str | None`. Handle commands (`help`, `quit`, `mesh`, `list agents`, `agent <id>`) and optionally pass natural language to the LLM. Use `ConversationBuffer` to keep recent turns for LLM context. Return `None` to signal quit.

### 3. Interactive session (interactive.py)

- **Run:** From repo root:  
  `python -m agents.cloud_reliability.interactive`  
  (or `agents/cloud_healing/interactive.py`, etc.)
- **Setup:** Add repo root and `agent-sdk` to `sys.path`, then instantiate the agent class (e.g. `CloudReliabilityAgent()`) and loop: `response = agent.answer(input("You> "))`; exit when `response is None`.
- **Behaviour:** Users can type natural language (when LLM is enabled), or commands like `help`, `mesh`, `list agents`, `agent cloud_healing`, `quit`. The agent uses the SDK for tools, policy, and audit; when `agent.regulated.interactive` is true (default when model is set), the agent is expected to support this interactive mode.

### 4. Programmatic use

- **From Python:** Add repo root and `agent-sdk` to `sys.path`, then:
  ```python
  from agents.cloud_reliability import CloudReliabilityAgent
  agent = CloudReliabilityAgent()
  result = agent.investigate_incident("INC-GCP-2025-001")
  ```
- **From control-plane / UI:** The platform can list agents (from registry or mesh) and invoke them via deployment or agent runtime; agents themselves are implemented here and use the SDK.

---

## How it works (flow)

1. **Load definition** – `RegulatedAgent(agent_id)` loads the definition from the control-plane (`GET /agents/{id}`) or, if that fails, from `config/agents/{agent_id}.yaml`. Interactive is default true when `model` is set.
2. **Kill-switch** – The SDK checks that the agent and its model are not disabled; otherwise it raises.
3. **Tool registration** – Each agent’s `_register_tools()` imports functions from `tools/mcp_*_tools` and calls `self.regulated.tools.register_impl(name, fn)`. Only tools in the definition’s `allowed_tools` can be resolved later via `self.regulated.tools.get(name)`.
4. **Execution** – For a **programmatic** call: the caller invokes domain methods (e.g. `investigate_incident()`), which use the gateway for tools, policy client for checks, and audit client for logging. For an **interactive** session: `interactive.py` calls `agent.answer(user_input)`; `answer()` handles commands or forwards to the LLM with conversation context.
5. **Agent-to-agent** – Some agents (e.g. cloud_reliability) call others (e.g. cloud_healing) via the tool `request_healing`, which uses the SDK’s `AgentInvocationGateway` (allowlist in `config/agent_invocation.yaml`). The healing agent exposes `execute_action()` invoked by the gateway.

---

## Creating a new agent

1. **Copy the template:** Duplicate `agents/template/` to e.g. `agents/my_agent/`.
2. **Definition:** Add `config/agents/my_agent.yaml` with `agent_id`, `domain`, `allowed_tools`, `policies`, `model`, etc. (see `config/agents/template.yaml`).
3. **agent.py:** Set `AGENT_ID = "my_agent"`, rename the class (e.g. `MyAgent`), implement `_register_tools()` (register only tools listed in the YAML), and implement `process()` and/or `answer()`.
4. **`__init__.py`:** Keep the **lazy-import** pattern from the template (using `__getattr__`). Do not add `from .agent import ...` at top level. This avoids a RuntimeWarning when the agent is run as `python -m agents.my_agent.agent` (e.g. in containers), because the package would otherwise load `agent` before it is executed as `__main__`.
5. **interactive.py:** Point the import to your agent class (e.g. `from agents.my_agent import MyAgent`) and run with `python -m agents.my_agent.interactive`.
6. **Tools:** Implement or reuse tools under `tools/` and register them by name in `_register_tools()`; only tools in `allowed_tools` will be callable. For **API-based tools** (created via Manage Tools with api_config), add the tool name to `allowed_tools` only—no `register_impl()` needed; see [Consuming a new tool](../docs/consuming-a-new-tool.md).

---

## Consuming a new tool

- **Code-based tool:** Add to `allowed_tools` in the agent YAML and register in `_register_tools()` with `self.regulated.tools.register_impl(name, fn)`.
- **API-based tool:** Add to `allowed_tools` in the agent YAML only; set the env vars required by the tool’s `api_config` where the agent runs. See [docs/consuming-a-new-tool.md](../docs/consuming-a-new-tool.md).

---

## Summary

| Concept | Where it lives | How it’s used |
|--------|----------------|----------------|
| Agent definition | `config/agents/<id>.yaml` or control-plane | Loaded by SDK; defines allowed_tools, model, interactive default, policies. |
| Agent implementation | `agents/<name>/agent.py` | RegulatedAgent + tool registration + domain methods + `answer()`. |
| Interactive REPL | `agents/<name>/interactive.py` | Run `python -m agents.<name>.interactive`; uses `answer()`. |
| Tools | `tools/mcp_*_tools/` | Registered in agent’s `_register_tools()`; only allowed_tools are resolvable. |
| Policy / audit | Via SDK | `self.regulated.policy.evaluate()`, `self.regulated.audit.log()`. |
| LLM | Via SDK | `self.regulated.llm` when model is set; use for reasoning and interactive replies. |

All agents are **governed** by the same SDK: one definition, one set of allowed tools, policy checks, and audit trail.
