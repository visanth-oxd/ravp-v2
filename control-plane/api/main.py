"""Main FastAPI application for control-plane."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import agents, audit, kill_switch, policies, tools
from .routes import auth, admin_tools, admin_policies, admin_agents, deployments, docker_build, gke_deploy, a2a, mesh, models as models_router, code_gen

app = FastAPI(
    title="Agent Factory Control-Plane",
    description="Platform services for agent governance, observability, and control",
    version="1.0.0"
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Register routes
app.include_router(agents.router)
app.include_router(tools.router)
app.include_router(policies.router)
app.include_router(audit.router)
app.include_router(kill_switch.router)
app.include_router(auth.router)
app.include_router(admin_tools.router)
app.include_router(admin_policies.router)
app.include_router(admin_agents.router)
app.include_router(deployments.router)
app.include_router(docker_build.router)
app.include_router(gke_deploy.router)
app.include_router(a2a.router)
app.include_router(mesh.router)
app.include_router(models_router.router)
app.include_router(code_gen.router)


@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "service": "agent-factory-control-plane",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}
