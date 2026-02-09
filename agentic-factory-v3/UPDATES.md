# Agent Factory v3 - Updates & Features

This document outlines the key features and recent updates to the Agent Factory v3 platform.

## Table of Contents
- [Overview](#overview)
- [Core Features](#core-features)
- [Recent Updates](#recent-updates)
- [Architecture](#architecture)
- [Getting Started](#getting-started)

---

## Overview

Agent Factory v3 is a governed, production-ready platform for building and deploying regulated AI agents. It provides:

- **Centralized Control**: Control plane manages agent definitions, policies, tools, and deployments
- **Governance**: Built-in RBAC, policies (Rego), audit logging, and kill-switch capabilities
- **Multi-Cloud**: Deploy to GKE, AKS, EKS, or run locally
- **LLM Flexibility**: Support for Google AI Studio, Vertex AI, OpenAI, Anthropic with runtime configuration
- **Agent Skills**: Structured capability framework for discovery and routing

---

## Core Features

### 1. Agent Registry
- **Agent Definitions**: YAML-based agent configurations stored in `config/agents/`
- **Versioning**: Semantic versioning with changelog tracking
- **RBAC**: Role-based access control (creator, visibility: public/private/group)
- **Personas**: Group-based visibility (business, cloud, platform)

### 2. Agent Skills System ✨ NEW
Agents now have structured capabilities for better discovery and routing:

```yaml
agent_id: cloud_reliability
purpose:
  goal: "Provide 24/7 automated incident response for GCP services"
skills:
  - incident_investigation
  - log_analysis
  - metric_analysis
  - root_cause_diagnosis
  - remediation_planning
```

**Benefits:**
- **Discovery**: Find agents by skill: `GET /agents?skill=incident_investigation`
- **LLM Context**: Skills are passed to LLM for self-awareness
- **Routing**: Enable skill-based agent-to-agent delegation
- **Separation**: Skills (what) vs Tools (how) vs Purpose (why)

### 3. Automatic Code Generation
When agents are created via UI/API, their implementation is auto-generated:

- **Template-based**: Uses `agents/template/` as base
- **Customization**: Placeholder replacement for agent_id, tools, policies
- **Complete Setup**: Generates `agent.py`, `interactive.py`, `__init__.py`, `README.md`
- **Manual Trigger**: API endpoint for regeneration: `POST /api/v2/code-gen/generate`

### 4. Runtime LLM Configuration
Configure LLM settings at deployment time, not in agent definition:

**UI Integration:**
- LLM Configuration section in Deploy Agent tab
- Fields: API Key, Provider, Custom Endpoint, GCP Project
- Available for Local Docker, GKE, AKS, EKS deployments

**Kubernetes Injection:**
```yaml
env:
  - name: GOOGLE_API_KEY
    value: "your-api-key"
  - name: GOOGLE_API_ENDPOINT
    value: "https://vertex-endpoint"
  - name: LLM_PROVIDER
    value: "vertex_ai"
  - name: GOOGLE_CLOUD_PROJECT
    value: "your-project"
```

**Benefits:**
- 🔄 Same image, different LLM backends per environment
- 🔒 API keys passed at deployment, not baked into code
- 🏢 Multi-tenant: Each deployment uses different endpoints
- 🧪 Easy testing: Dev uses AI Studio, Prod uses Vertex AI

### 5. Multi-Provider LLM Support
Unified API for multiple LLM providers:

**Supported Providers:**
- **Google AI Studio**: Simple API key-based (`google` provider)
- **Vertex AI**: GCP-based with project/region (`vertex_ai` provider)
- **OpenAI**: GPT models (`openai` provider)
- **Anthropic**: Claude models (`anthropic` provider)
- **Custom Endpoints**: Any Google-compatible API

**Implementation:**
```python
# In agent code
self.regulated.llm.generate("prompt")  # Works with any provider

# Provider auto-detection from model name or explicit configuration
# Falls back gracefully if LLM unavailable
```

### 6. Policy Enforcement
OPA (Open Policy Agent) based governance:

```yaml
agent_id: payment_retry
policies:
  - payments/retry
  - payments/retry_schedule
```

```python
# In agent code
policy_result = self.regulated.policy.evaluate("payments/retry", {
    "amount": 5000,
    "previous_retries": 0,
    "beneficiary_blocked": False
})
# Raises PolicyDeniedError if denied
```

**Policy Files:** `policies/{domain}/{policy}.rego`

### 7. Audit Logging
All agent actions are logged for compliance:

```python
# Tool calls
self.regulated.audit.log_tool_call(
    agent_id=self.agent_id,
    tool_name="get_payment_exception",
    args={"exception_id": "EX-123"},
    result_summary="Found exception"
)

# Decisions
self.regulated.audit.log_decision(
    agent_id=self.agent_id,
    decision="RETRY",
    context={"confidence": 0.9}
)

# Policy checks
self.regulated.audit.log_policy_check(
    agent_id=self.agent_id,
    policy_id="payments/retry",
    input_data={...},
    result={"allowed": True}
)
```

**Storage:** `data/audit/` (JSON files, one per agent)

### 8. Platform UI (Streamlit)
Modern web interface for agent management:

**Tabs:**
- **Create Agent**: Define new agents with skills, tools, policies
- **My Agents**: Edit/manage your agents
- **Browse Agents**: Simplified view with action icons (👁️ View, ✏️ Edit, 🚀 Deploy)
- **Deploy Agent**: Build & deploy to Local Docker, GKE, AKS, EKS
- **Manage Tools/Policies** (Admin only)

**Features:**
- Code generation status indicator
- LLM configuration inputs per deployment target
- Deployment mode: Build & Push OR Deploy existing image
- Kaniko in-cluster builds (no Docker daemon needed)

### 9. Kill-Switch
Emergency stop for agents or models:

```bash
# Disable an agent
curl -X POST http://localhost:8010/kill-switch/agents/payment_retry/disable

# Disable a model
curl -X POST http://localhost:8010/kill-switch/models/gpt-4/disable
```

**Effect:** Agents check kill-switch on initialization; disabled agents/models cannot run.

### 10. Agent-to-Agent Communication (A2A)
Mesh networking for agent collaboration:

```python
# From one agent, invoke another
healing_result = self.agent_client.invoke_agent(
    target_id="cloud_healing",
    action="resize_cloud_sql_instance",
    params={"instance_id": "db-1", "new_tier": "db-n1-standard-4"}
)
```

**Discovery:** Agents advertise capabilities in `capability_for_other_agents` field

---

## Recent Updates

### December 2025 - February 2026

#### ✅ Agent Skills System
- Added `skills` field to agent schema
- Skills exposed via `agent.skills` property
- Skills passed to LLM in system prompts
- Skill-based filtering in API: `GET /agents?skill=X`
- Updated example agents with meaningful skills

#### ✅ Purpose/Goal Utilization
- Enhanced LLM prompts to use `agent.purpose` consistently
- Template agent shows best practices
- Cloud reliability agent updated to use purpose + skills

#### ✅ UI Improvements
- Added skills input field in Create/Edit Agent tabs
- Simplified Browse Agents section (icon-based actions)
- Removed verbose deployment workflows from Browse
- Moved LLM config to "Step 2: Configure and Deploy"
- Cleaner status messages (removed internal paths)

#### ✅ Code Generation Enhancements
- Automatic code generation on agent creation
- Manual trigger via UI button
- Deletion cleanup (removes generated code when agent deleted)
- Audit logging for code generation events

#### ✅ Runtime LLM Configuration
- LLM settings passed at deployment, not in definition
- UI fields for API Key, Provider, Endpoint, Project
- Kubernetes manifest generation includes LLM env vars
- Support for secrets-based API keys (optional)

#### ✅ Multi-Provider LLM
- Unified `LLMProvider` interface
- Factory pattern for provider selection
- Support for Google AI Studio, Vertex AI, OpenAI, Anthropic
- Auto-detection from model names
- Graceful degradation when LLM unavailable

#### ✅ Audit & Governance
- Policy evaluation logging
- Agent lifecycle audit (creation, deletion)
- Tool call audit trail
- Decision logging with context

#### ✅ SSL/Certificate Handling
- Added `ca-certificates` to all Dockerfiles
- `--trusted-host` flags for pip in controlled environments
- Works in corporate networks with custom CAs

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Platform UI (Streamlit)                 │
│  Create • Edit • Browse • Deploy • Manage Tools/Policies    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    Control Plane (FastAPI)                   │
├─────────────────────────────────────────────────────────────┤
│ • Agent Registry     • Policy Registry   • Tool Registry    │
│ • Kill-Switch        • Audit Store       • RBAC             │
│ • Code Generator     • Deployment Mgmt   • Docker/Kaniko    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    Agent Runtime (SDK)                       │
├─────────────────────────────────────────────────────────────┤
│ RegulatedAgent:                                              │
│   • Load definition from registry                            │
│   • Check kill-switch                                        │
│   • PolicyClient (evaluate policies)                         │
│   • ToolGateway (only allowed tools)                         │
│   • AuditClient (log all actions)                            │
│   • LLMProvider (multi-provider support)                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  Deployment Targets                          │
├─────────────────────────────────────────────────────────────┤
│ • Local Docker       • GKE (Google)     • AKS (Azure)       │
│ • EKS (AWS)          • Cloud Run                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Agent Creation:**
   ```
   UI → Control Plane → Agent Registry (YAML) → Code Generator → agents/{id}/
   ```

2. **Agent Execution:**
   ```
   Agent Runtime → Load Definition → Check Kill-Switch → Initialize SDK
   → Use Tools → Check Policies → Log Audit → Execute Action
   ```

3. **Deployment:**
   ```
   UI → Control Plane → Docker Build → Push to Registry → K8s Manifest
   → Apply to Cluster (with LLM config as env vars)
   ```

---

## Getting Started

### Prerequisites
- Python 3.11+
- Docker (for local deployments and builds)
- kubectl (for Kubernetes deployments)
- OPA (optional, for policy evaluation)

### Quick Start

1. **Start Control Plane:**
   ```bash
   cd agentic-factory-v3
   python run_control_plane.py
   # Runs on http://localhost:8010
   ```

2. **Start Platform UI:**
   ```bash
   streamlit run platform_ui/app.py
   # Opens in browser at http://localhost:8501
   ```

3. **Set API Key (for LLM):**
   ```bash
   export GOOGLE_API_KEY="your-key"
   ```

4. **Create an Agent:**
   - Go to "Create Agent" tab
   - Fill in: Agent ID, Purpose, Skills
   - Select Tools and Policies
   - Click "Create Agent"
   - Code is auto-generated in `agents/{agent_id}/`

5. **Deploy Agent:**
   - Go to "Deploy Agent" tab
   - Select agent
   - Choose deployment target (Local Docker / GKE / AKS / EKS)
   - Configure LLM settings (API key, provider, endpoint)
   - Build & Push image
   - Deploy

### Example: Create Cloud Reliability Agent

```bash
# Via API
curl -X POST http://localhost:8010/api/v2/agent-definitions \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "my_cloud_agent",
    "version": "1.0.0",
    "domain": "cloud_platform",
    "risk_tier": "low",
    "purpose": {
      "goal": "Monitor and respond to cloud incidents"
    },
    "skills": [
      "incident_investigation",
      "log_analysis"
    ],
    "allowed_tools": [
      "get_log_entries",
      "get_metric_series"
    ],
    "policies": [],
    "model": "auto"
  }'

# Code is auto-generated at: agents/my_cloud_agent/
```

### Example: Deploy with Runtime LLM Config

```bash
# Deploy to GKE with Vertex AI
curl -X POST http://localhost:8010/api/v2/deployments/apply \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "my_cloud_agent",
    "image_url": "gcr.io/project/agent-my_cloud_agent:1.0.0",
    "deployment_type": "gke",
    "environment": "prod",
    "namespace": "agents",
    "replicas": 2,
    "port": 8080,
    "llm_config": {
      "api_key": "your-vertex-api-key",
      "provider": "vertex_ai",
      "project": "your-gcp-project",
      "endpoint": "https://us-central1-aiplatform.googleapis.com"
    }
  }'
```

### Example: Interactive Session

```bash
cd agents/cloud_reliability
python -m agents.cloud_reliability.interactive

# Agent loads definition, checks kill-switch, initializes LLM
# Commands:
#   investigate INC-123  - investigate incident
#   help                 - show commands
#   mesh                 - show other agents
#   quit                 - exit
```

---

## Configuration

### Agent Definition Schema

```yaml
agent_id: string              # Unique identifier
version: string               # Semantic version (x.y.z)
domain: string                # Business domain (payments, cloud, etc)
group: string                 # Persona group (business, cloud, platform)
risk_tier: low|medium|high    # Governance tier

purpose:
  goal: string                # Why this agent exists (mission)
  instructions_prefix: string # Optional LLM instructions

skills:                       # High-level capabilities (NEW)
  - string                    # e.g., incident_investigation

allowed_tools:                # Technical tools
  - string                    # e.g., get_log_entries

policies:                     # Governance policies
  - string                    # e.g., payments/retry

model: string                 # LLM model (auto, gemini-2.5-flash, etc)
llm_provider: string          # Optional: google, vertex_ai, openai, anthropic
llm_config:                   # Provider-specific config
  project: string
  region: string
  base_url: string

confidence_threshold: float   # Min confidence (0.0-1.0)
human_in_the_loop: boolean    # Require human approval

rbac:
  creator: string             # Creator email
  visibility: string          # public, private, group:{name}
```

### Environment Variables

```bash
# Control Plane
CONTROL_PLANE_URL=http://localhost:8010
POLICIES_DIR=./policies
TOOLS_DIR=./config/tools

# Agent Runtime
GOOGLE_API_KEY=your-key              # Google AI Studio / Vertex AI
GOOGLE_API_ENDPOINT=https://...     # Optional custom endpoint
LLM_PROVIDER=google                  # auto, google, vertex_ai, openai, anthropic
GOOGLE_CLOUD_PROJECT=your-project    # For Vertex AI

OPENAI_API_KEY=your-key              # For OpenAI
ANTHROPIC_API_KEY=your-key           # For Anthropic
```

---

## API Reference

### Agent Registry

```bash
# List agents (with skill filter)
GET /agents?skill=incident_investigation

# Get agent definition
GET /agents/{agent_id}

# Create agent (auto-generates code)
POST /api/v2/agent-definitions

# Update agent
PUT /api/v2/agent-definitions/{agent_id}

# Delete agent (removes code)
DELETE /api/v2/agent-definitions/{agent_id}
```

### Code Generation

```bash
# Generate agent code
POST /api/v2/code-gen/generate
{
  "agent_id": "my_agent",
  "overwrite": false
}

# Validate code exists
GET /api/v2/code-gen/validate/{agent_id}

# Bulk generate
POST /api/v2/code-gen/bulk-generate
```

### Policies

```bash
# List policies
GET /policies

# Evaluate policy
POST /policies/{policy_id}/evaluate
{
  "amount": 5000,
  "previous_retries": 0
}
```

### Kill-Switch

```bash
# Disable agent
POST /kill-switch/agents/{agent_id}/disable

# Enable agent
POST /kill-switch/agents/{agent_id}/enable

# Disable model
POST /kill-switch/models/{model_id}/disable
```

### Deployments

```bash
# Deploy agent (with LLM config)
POST /api/v2/deployments/apply
{
  "agent_id": "my_agent",
  "image_url": "gcr.io/project/agent:tag",
  "deployment_type": "gke",
  "environment": "prod",
  "llm_config": {
    "api_key": "key",
    "provider": "vertex_ai",
    "endpoint": "https://...",
    "project": "gcp-project"
  }
}

# List deployments
GET /api/v2/deployments

# Get deployment
GET /api/v2/deployments/{deployment_id}
```

---

## Best Practices

### 1. Agent Design
- **Single Responsibility**: One agent, one domain (payments, cloud, fraud)
- **Purpose + Skills**: Clearly define why (purpose) and what (skills)
- **Tool Selection**: Only include needed tools (least privilege)
- **Policy Usage**: Apply policies for high-risk actions

### 2. LLM Configuration
- **Dev/Test**: Use Google AI Studio with simple API key
- **Staging**: Use Vertex AI with test project
- **Production**: Use Vertex AI with regional endpoints, managed keys
- **Multi-tenant**: Different deployments = different LLM configs

### 3. Skills vs Tools
- **Skills**: High-level (incident_investigation, payment_processing)
- **Tools**: Low-level (get_log_entries, retry_payment)
- Mapping: One skill uses multiple tools

### 4. Governance
- **Policies**: Required for high-risk actions (payments, fraud, deletions)
- **Audit**: Log all tool calls and decisions
- **RBAC**: Use group-based visibility for enterprise
- **Kill-Switch**: Test emergency stop procedures

### 5. Deployment
- **Images**: Tag with agent version (agent-name:1.0.0)
- **Secrets**: Use Kubernetes secrets for API keys in production
- **Monitoring**: Deploy to staging first, validate, then prod
- **Rollback**: Keep previous versions for quick rollback

---

## Troubleshooting

### Agent Code Not Generated
```bash
# Check status
curl http://localhost:8010/api/v2/code-gen/validate/my_agent

# Manually trigger
curl -X POST http://localhost:8010/api/v2/code-gen/generate \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "my_agent"}'
```

### LLM Not Available
```bash
# Check env var
echo $GOOGLE_API_KEY

# Test provider
curl -X POST http://localhost:8010/api/v2/agent-definitions/my_agent/test-llm

# Agent runs without LLM (graceful degradation) but can't use reasoning
```

### Policy Evaluation Fails
```bash
# Check OPA installed
opa version

# Test policy manually
opa eval -d policies/payments/retry.rego \
  -i input.json \
  'data.payments.retry.allow'

# Fallback: Stub implementation used if OPA unavailable
```

### Deployment Fails (Kaniko)
```bash
# Check RBAC permissions
kubectl get clusterrole kaniko-builder

# Apply if missing
kubectl apply -f deploy/gke/kubernetes/control-plane-rbac-builds.yaml

# Check Kaniko job logs
kubectl logs -n ravp job/kaniko-build-{agent-id}-{timestamp}
```

---

## Next Steps

1. **Add More Skills**: Define skill taxonomies for your domain
2. **Custom Policies**: Write Rego policies for your business rules
3. **Tool Development**: Build domain-specific tools
4. **Monitoring**: Add Prometheus metrics for agents
5. **Multi-Region**: Deploy agents across regions for HA
6. **A2A Workflows**: Build complex multi-agent workflows

---

## Support & Documentation

- **Main README**: [README.md](README.md)
- **Agent Development**: [agents/agents.md](agents/agents.md)
- **Policy System**: [policies/policies.md](policies/policies.md)
- **Control Plane**: [control-plane/control-plane.md](control-plane/control-plane.md)
- **Deployment**: [deploy/gke/README.md](deploy/gke/README.md)

---

## Version History

- **v3.0** (Feb 2026): Agent skills, runtime LLM config, enhanced UI
- **v2.5** (Dec 2025): Multi-provider LLM support
- **v2.0** (Nov 2025): Code generation, audit logging
- **v1.0** (Oct 2025): Initial release with agent registry, policies, tools

---

**Built with:** Python, FastAPI, Streamlit, Kubernetes, OPA, Google Gemini

**License:** Internal Use Only
