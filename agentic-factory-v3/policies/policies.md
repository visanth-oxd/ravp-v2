# Policies

The **policies** folder holds **Rego** policy files that the platform uses to decide whether an action is allowed (e.g. “can we retry this payment?”, “should we block this transaction?”). Agents list policy IDs in their definition; at runtime the Agent SDK calls the control-plane to **evaluate** a policy with input data. The control-plane loads these files, runs them via **OPA** (Open Policy Agent) when available, or falls back to a **stub** for known policies. The Platform UI (Manage Policies tab) lets admins view and edit policy content; changes are written back to this folder.

---

## What’s in this folder

Policies are grouped by **domain** in subfolders. The **policy ID** is the path from `policies/` with `.rego` removed and path separators as `/` (e.g. `policies/payments/retry.rego` → `payments/retry`).

| Domain | Files | Policy IDs (examples) |
|--------|--------|------------------------|
| **payments** | approval.rego, failure_handling.rego, refund.rego, retry.rego, retry_schedule.rego, reversal.rego | payments/retry, payments/approval, … |
| **fraud** | block.rego, flag.rego, investigation.rego | fraud/block, fraud/flag, fraud/investigation |
| **compliance** | aml_check.rego, kyc_verification.rego | compliance/aml_check, compliance/kyc_verification |
| **credit** | approval.rego, limit_increase.rego | credit/approval, credit/limit_increase |
| **customer_service** | account_modification.rego, complaint_resolution.rego | customer_service/account_modification, customer_service/complaint_resolution |

Each file is a Rego **package** whose name matches the policy ID with `/` replaced by `.` (e.g. `package payments.retry`, `package fraud.block`). The control-plane and OPA evaluate the `allow` rule (and optionally `deny`) to produce allow/deny and a reason.

---

## How it’s used

- **Agent definitions** – In `config/agents/<agent_id>.yaml`, the `policies` list references these policy IDs (e.g. `payments/retry`). Only policies in this list are used by that agent.
- **Agent SDK** – When an agent needs a decision, it calls the control-plane: `POST /policies/{policy_id}/evaluate` with a JSON body (the `input` to the Rego policy). The SDK’s `PolicyClient.evaluate(policy_id, input_data)` does this and returns `{allowed, reason, details}`; it can raise `PolicyDeniedError` when the policy denies.
- **Control-plane** – The policy registry (`control-plane/policy_registry/loader.py`) scans this folder for `*.rego`, builds the list of policy IDs for `GET /policies`, and for evaluate maps `policy_id` to the file `policies/{policy_id}.rego` (with `/` as path separator). Evaluation uses OPA if installed (`opa eval -d <policy_file> -i <input_json> data.<package>.allow`), otherwise a stub for known policies (e.g. payments/retry).
- **Platform UI** – Manage Policies (admin) lists policies by domain (`GET /api/v2/admin/policies/domains`), gets content (`GET /api/v2/admin/policies/{policy_id}`), and saves changes (`PUT /api/v2/admin/policies/{policy_id}` with `{"content": "..."}`), which writes directly to the file under `policies/`.

---

## How it works

1. **Discovery** – The control-plane scans `policies/` with `rglob("*.rego")` and derives policy IDs from relative paths (e.g. `payments/retry.rego` → `payments/retry`). The public API `GET /policies` and the admin API use this list.
2. **Evaluation** – For `POST /policies/{policy_id}/evaluate`, the loader resolves the file path as `policies/{policy_id}.rego`. If OPA is available, it runs `opa eval` with that file and the request body as input; the query is `data.<package>.allow` (package = `policy_id` with `/` → `.`). If OPA is not installed or fails, a stub is used for some policy IDs (e.g. payments/retry) to return a simple allow/deny; others get “unknown_policy” and deny.
3. **Stub** – The stub exists so the platform works without installing OPA. It only implements a subset of rules (e.g. payments/retry: beneficiary blocked → deny, escalation requested → allow, amount and retry limits). For full rules, install OPA and ensure it’s on `PATH`.
4. **Editing** – Admin updates policy content via the API; the control-plane writes the new Rego text to `policies/{policy_id}.rego`, creating parent directories if needed.

---

## Rego structure (conventions)

- **Package** – Must match the policy ID: `package payments.retry` for `payments/retry`, `package fraud.block` for `fraud/block`.
- **Allow / deny** – The loader queries `data.<package>.allow`. Policies typically define `default allow = false` and then set `allow` (and optionally `deny`) based on `input` (the JSON body of the evaluate request). Deny rules can be separate; the evaluator treats “allow true” as allowed and “allow false” or OPA failure as denied.
- **Input** – The evaluate request body is the Rego `input`. Agents pass domain-specific fields (e.g. for payments/retry: `amount`, `previous_retries`, `error_type`, `escalation_requested`, `beneficiary_blocked`, `customer_tier`, etc.). Design your Rego to use the same field names the agent sends.

Example (conceptual):

```rego
package payments.retry
default allow = false
allow if { input.amount <= 10000; input.previous_retries < 2 }
allow if { input.escalation_requested == true }
deny if { input.beneficiary_blocked == true }
```

---

## Configuration

- **POLICIES_DIR** – Environment variable (optional). If set, the control-plane policy registry uses this directory instead of `repo_root/policies`. Useful when the app runs from a different root or in a container.

---

## Summary

| Concept | Where | Role |
|--------|--------|------|
| Policy files | `policies/<domain>/<name>.rego` | Rego source; one file per policy. |
| Policy ID | Path from `policies/` without `.rego`, `/` as separator | e.g. `payments/retry`, `fraud/block`. Used in agent definitions and API. |
| List | Control-plane `policy_registry/loader.py` | Scans folder; `GET /policies` and admin list. |
| Evaluate | Control-plane `policy_registry/loader.py` | Resolves file, runs OPA or stub; `POST /policies/{id}/evaluate`. |
| Edit | Control-plane admin API | `PUT /api/v2/admin/policies/{policy_id}` writes to `policies/{policy_id}.rego`. |
| Agent use | Agent definition `policies: [payments/retry, ...]` + SDK `PolicyClient.evaluate()` | Agents only call policies listed in their config; SDK calls control-plane evaluate. |

Policies are the **governance layer** for agent actions: they live in this folder, are evaluated by the control-plane (OPA or stub), and are edited via the Platform UI (Manage Policies).
