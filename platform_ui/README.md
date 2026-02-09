# Platform UI

The **Platform UI** is a Streamlit web app for **RAVP v2** (REgulated Agent Vending Platform). It lets you create and manage agents, browse them by domain, deploy agents, manage tools and policies (admin), view version history, and see a “How it works” flow. All data and actions go through the **control-plane** API. You must log in to use the app; **Manage Tools** and **Manage Policies** require an admin account (`admin@platform.com`).

---

## What’s in this folder

| File | Purpose |
|------|--------|
| **app.py** | Single Streamlit application: sidebar login, nine tabs, all UI logic and API calls. |

There are no separate pages or components; everything is in `app.py`.

---

## Tabs (overview)

| Tab | Purpose |
|-----|--------|
| **Create Agent** | Form to create a new agent: agent ID, domain, risk tier, version, purpose, model (e.g. Auto / Gemini), confidence threshold, human-in-the-loop, allowed tools, policies. Submits to `POST /api/v2/agent-definitions`. |
| **My Agents** | List of agents you can see (from `GET /agents` with RBAC). Per agent: view, **Update** (edit definition), **Delete**, **Version History** (expandable). Update/delete call the control-plane admin agent-definitions API. |
| **Browse Agents** | Agents grouped by **domain** (Payments, Cloud Platform, etc.). For each agent: **Deploy** (build image, choose env, deploy), **Interact** (send a message; uses SDK to run agent and show reply), **View Details** (full definition). Uses `GET /agents`, deployment and Docker build APIs. |
| **Deploy Agent** | Select an agent and deployment target (Local Docker, GKE, AKS, EKS). For each target: build/push image (control-plane Docker build API), copy commands, or deploy locally. Records deployment via control-plane deployments API. |
| **Deployed Agents** | List deployments from `GET /api/v2/deployments`, grouped by environment. Per deployment: status, type, endpoint, **Interact** (query the deployed agent), **Update** status. |
| **Manage Tools** | *(Admin only.)* List tools by domain (`GET /api/v2/admin/tools/domains`), migrate flat registry to versioned, add tool, edit tool (description, data sources, PII/risk, human approval), view **Version History** per tool. |
| **Manage Policies** | *(Admin only.)* List policies by domain, edit Rego content per policy, save (writes to repo via control-plane). Add new policy by ID and content. |
| **Version History** | Select an agent from a dropdown (from agent-definitions or fallback `GET /agents`). Shows current version, total versions, and history entries (version, previous, timestamp, changes). Per entry: tools and policies for that version. Uses `GET /api/v2/agent-definitions/{id}/history`. |
| **How it works** | Diagram and short description of the flow: User → Control Plane → Agent Registry → Regulated Agent → Policy / LLM / Tools / Mesh / Audit → Response. |

---

## Login and roles

- **Sidebar** – Email and password; **Login** calls `POST /api/v2/auth/login`. If the control-plane is unreachable, the UI falls back to a demo login and assigns role by email.
- **Roles** – `platform_admin` (e.g. `admin@platform.com`, `platform@admin.com`) and `agent_creator`. Stored in session after login.
- **Admin-only tabs** – **Manage Tools** and **Manage Policies** show a warning if you are not `platform_admin`; the control-plane returns 403 for admin endpoints when the user is not admin.
- **Logout** – Clears session (logged_in, token, user_role, user_email) and reruns the app.

All requests to the control-plane that need auth send `Authorization: Bearer <token>` (and optionally `X-User-Email` where used by the API).

---

## How it works (flow)

1. **Load** – User opens the app; Streamlit runs `app.py`. If not logged in, only the login prompt and tab list are shown; after login, all nine tabs are rendered.
2. **Data** – Each tab that needs data calls the control-plane: e.g. `GET /agents`, `GET /api/v2/agent-definitions`, `GET /tools`, `GET /policies`, `GET /api/v2/deployments`, `GET /api/v2/admin/tools/domains`, `GET /api/v2/admin/policies/domains`. Lists are filtered by RBAC where applicable.
3. **Actions** – Create agent → `POST /api/v2/agent-definitions`. Update/delete agent → `PUT` / `DELETE /api/v2/agent-definitions/{id}`. Deploy → deployment and Docker build APIs. Manage tools/policies → admin tools/policies APIs. Version history → agent-definitions history endpoint.
4. **Interact** – When you use **Interact** (Browse or Deployed Agents), the UI instantiates the agent via the SDK (`RegulatedAgent`), calls `answer()` (or equivalent), and displays the response. This runs in the Streamlit process and requires the control-plane and agent code to be available.

---

## Running the UI

**Prerequisites:** Control-plane running (e.g. `python run_control_plane.py` on port 8010).

For full local setup (control-plane + UI), see **[docs/RUN-LOCALLY.md](../docs/RUN-LOCALLY.md)**.

From the **repo root**:

```bash
streamlit run platform_ui/app.py
```

Or from the `platform_ui` directory:

```bash
streamlit run app.py
```

The app opens in the browser (default `http://localhost:8501`). Set the control-plane URL if it’s not on localhost:

```bash
API_URL=http://localhost:8010 streamlit run platform_ui/app.py
```

---

## Configuration

| Variable | Purpose |
|----------|--------|
| **API_URL** | Control-plane base URL (default `http://localhost:8010`). All requests use this. |

No config files in this folder; everything is driven by `API_URL` and session state (token, role, email).

---

## Dependencies

- **streamlit** – Web UI.
- **requests** – HTTP calls to the control-plane.

Install from the repo root:

```bash
pip install -r requirements.txt
```

---

## Summary

| Concept | Where | Role |
|--------|--------|------|
| App entry | `app.py` | Single Streamlit app; `st.set_page_config`, title, sidebar login, tabs. |
| Tabs | `app.py` | Create Agent, My Agents, Browse Agents, Deploy Agent, Deployed Agents, Manage Tools, Manage Policies, Version History, How it works. |
| Auth | Sidebar + session | Login → control-plane `/api/v2/auth/login`; token and role in `st.session_state`; sent as `Authorization: Bearer <token>`. |
| Control-plane | `API_BASE_URL` | All reads/writes go to the control-plane (agents, tools, policies, audit, kill-switch, admin, deployments, models). |
| Interact | Browse / Deployed Agents | SDK `RegulatedAgent` + agent’s `answer()` in process; result shown in UI. |

The Platform UI is the main way to create, browse, deploy, and manage agents and their tools and policies through the control-plane.
