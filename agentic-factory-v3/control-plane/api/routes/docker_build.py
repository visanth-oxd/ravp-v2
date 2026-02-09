"""Docker build and push API endpoints."""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel

# Add control-plane to path for imports
control_plane_dir = Path(__file__).resolve().parent.parent.parent
if str(control_plane_dir) not in sys.path:
    sys.path.insert(0, str(control_plane_dir))

from docker_build.build_service import build_and_push, detect_registry_type, is_docker_available
from docker_build.kaniko_build import build_via_kaniko_job, _running_in_cluster, _is_artifact_registry
from agent_registry.storage import load_agent
from .auth import require_auth

router = APIRouter(prefix="/api/v2/docker", tags=["docker-build"])


@router.get("/status")
def docker_status(_=Depends(require_auth)) -> Dict[str, Any]:
    """
    Check if Docker is available, or if in-cluster Kaniko build is available.
    When running in-cluster with Artifact Registry, Build & Push uses a Kaniko Job (no Docker needed).
    """
    in_cluster = _running_in_cluster()
    if in_cluster:
        return {
            "available": True,
            "message": "In-cluster Kaniko build available for Artifact Registry / GCR. Use an image URL like us-central1-docker.pkg.dev/PROJECT/REPO/agent-NAME:TAG",
            "hint": "Build & Push will create a Kaniko Job. Ensure RBAC allows creating Jobs/ConfigMaps and the build service account can push to Artifact Registry.",
            "mode": "kaniko",
        }
    available, message = is_docker_available()
    return {
        "available": available,
        "message": message,
        "hint": "Start Docker Desktop on this machine, or run the control-plane in-cluster for Kaniko builds.",
        "mode": "docker",
    }


class BuildRequest(BaseModel):
    agent_id: str
    registry_url: str  # Full URL: gcr.io/project/image:tag, acr.azurecr.io/image:tag, etc.
    tag: str = "latest"
    dockerfile_path: Optional[str] = None
    build_args: Optional[Dict[str, str]] = None
    credentials: Optional[Dict[str, str]] = None  # For Docker Hub: {"username": "...", "password": "..."}


class BuildResponse(BaseModel):
    success: bool
    image_url: str
    steps: list
    error: Optional[str] = None


@router.post("/build-and-push")
def build_and_push_image(
    request: BuildRequest,
    background_tasks: BackgroundTasks,
    _=Depends(require_auth)
) -> BuildResponse:
    """
    Build Docker image and push to registry.
    
    When the control-plane runs **in-cluster** and the registry is **Artifact Registry**
    (or GCR), a Kaniko Job is used so no Docker daemon is needed. Otherwise uses local
    Docker build and push.
    
    Supported registries:
    - Artifact Registry / GCR: in-cluster Kaniko build when running in K8s
    - ACR, ECR, Docker Hub: local Docker only
    """
    # Validate agent definition exists (config/agents/<agent_id>.yaml)
    agent_def = load_agent(request.agent_id)
    if not agent_def:
        raise HTTPException(
            status_code=400,
            detail=f"Agent definition not found: {request.agent_id}. Create the agent first (config/agents/{request.agent_id}.yaml) and ensure agent code exists under agents/{request.agent_id}/.",
        )
    # In-cluster + Artifact Registry (or GCR): use Kaniko Job
    if _running_in_cluster() and _is_artifact_registry(request.registry_url):
        # Default: agents (in any namespace) reach control-plane via K8s DNS
        # http://<service>.<control-plane-namespace>.svc.cluster.local:8010
        _cp_ns = os.environ.get("POD_NAMESPACE", "ravp")
        _cp_svc = os.environ.get("CONTROL_PLANE_SERVICE_NAME", "ravp-control-plane")
        _default_cp_url = f"http://{_cp_svc}.{_cp_ns}.svc.cluster.local:8010"
        control_plane_url = (request.build_args or {}).get(
            "CONTROL_PLANE_URL",
            _default_cp_url,
        )
        success, image_url, err = build_via_kaniko_job(
            agent_id=request.agent_id,
            registry_url=request.registry_url,
            tag=request.tag,
            control_plane_url=control_plane_url,
            namespace=os.environ.get("POD_NAMESPACE", "ravp"),
            timeout_seconds=600,
        )
        if success:
            return BuildResponse(success=True, image_url=image_url, steps=[
                {"step": "kaniko-job", "status": "completed", "message": f"Built and pushed: {image_url}"},
            ], error=None)
        return BuildResponse(
            success=False,
            image_url="",
            steps=[{"step": "kaniko-job", "status": "failed", "message": err}],
            error=err,
        )

    # Local Docker build
    from docker_build.build_service import get_repo_root
    dockerfile_path = None
    if request.dockerfile_path:
        dockerfile_path = Path(request.dockerfile_path)
    else:
        repo_root = get_repo_root()
        dockerfile_path = repo_root / f"Dockerfile.{request.agent_id}"
    result = build_and_push(
        request.agent_id,
        request.registry_url,
        request.tag,
        dockerfile_path,
        request.build_args,
        request.credentials
    )
    return BuildResponse(**result)


@router.get("/detect-registry")
def detect_registry(registry_url: str, _=Depends(require_auth)) -> Dict[str, str]:
    """Detect registry type from URL."""
    registry_type = detect_registry_type(registry_url)
    return {
        "registry_url": registry_url,
        "registry_type": registry_type
    }
