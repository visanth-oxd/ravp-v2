"""Deployment Registry API - track and manage agent deployments."""

import os
import sys
import tempfile
import yaml
import requests as requests_lib
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

# Add control-plane to path for imports
control_plane_dir = Path(__file__).resolve().parent.parent.parent
if str(control_plane_dir) not in sys.path:
    sys.path.insert(0, str(control_plane_dir))

from deployment_registry.storage import (
    load_deployment,
    list_deployments,
    save_deployment,
    delete_deployment,
    get_deployments_for_agent,
    list_environments,
)
from deployment_registry.manifests import generate_manifest, manifest_to_yaml, _k8s_safe_name
from .auth import require_auth

router = APIRouter(prefix="/api/v2/deployments", tags=["deployments"])


class DeploymentRequest(BaseModel):
    agent_id: str
    environment: str
    deployment_type: str  # "local", "gke", "aks", "eks", "cloud_run", etc.
    status: str = "deployed"  # "deployed", "running", "stopped", "failed"
    endpoint: Optional[str] = None
    image_url: Optional[str] = None  # Container image URL
    metadata: Optional[Dict[str, Any]] = None
    llm_config: Optional[Dict[str, Any]] = None  # Runtime LLM configuration


class DeployApplyRequest(BaseModel):
    """Request to generate manifest and optionally apply to cluster (when control-plane runs in-cluster)."""
    agent_id: str
    image_url: str
    namespace: str = "agents"
    replicas: int = 1
    port: int = 8080
    control_plane_url: str = "http://ravp-control-plane.ravp.svc.cluster.local:8010"
    deployment_type: str = "gke"  # "gke", "aks", "eks"
    environment: str = "gke-prod"
    llm_config: Optional[Dict[str, Any]] = None  # Runtime LLM configuration (api_key, endpoint, provider)


def _running_in_cluster() -> bool:
    return bool(os.environ.get("KUBERNETES_SERVICE_HOST"))


def _apply_manifest_in_cluster(manifest_yaml: str) -> tuple[bool, str]:
    """Apply YAML manifest using in-cluster K8s API (create or replace so redeploy works).
    Returns (success, message)."""
    try:
        from kubernetes import client, config
        from kubernetes.dynamic import DynamicClient
    except ImportError:
        return False, "kubernetes package not installed"
    try:
        config.load_incluster_config()
    except Exception as e:
        return False, f"Failed to load in-cluster config: {e}"
    k8s_client = client.ApiClient()
    dyn = DynamicClient(k8s_client)
    # Map Kind -> (api_version, plural)
    kind_to_resource = {
        "Deployment": ("apps/v1", "deployments"),
        "Service": ("v1", "services"),
    }
    docs = list(yaml.safe_load_all(manifest_yaml))
    for doc in docs:
        if not doc or "kind" not in doc:
            continue
        kind = doc["kind"]
        if kind not in kind_to_resource:
            continue
        api_version, plural = kind_to_resource[kind]
        meta = doc.get("metadata", {})
        name = meta.get("name")
        namespace = meta.get("namespace", "default")
        if not name:
            continue
        try:
            resource = dyn.resources.get(api_version=api_version, kind=kind)
            try:
                existing = resource.get(namespace=namespace, name=name)
            except Exception as get_err:
                if getattr(get_err, "status", None) == 404:
                    existing = None
                else:
                    raise get_err
            if existing:
                meta = getattr(existing, "metadata", None) or (existing if isinstance(existing, dict) else {}).get("metadata", {})
                rv = meta.get("resourceVersion") if isinstance(meta, dict) else getattr(meta, "resourceVersion", None)
                if rv:
                    doc["metadata"]["resourceVersion"] = rv
                if kind == "Service":
                    spec = getattr(existing, "spec", None) or (existing if isinstance(existing, dict) else {}).get("spec", {})
                    cluster_ip = spec.get("clusterIP") if isinstance(spec, dict) else getattr(spec, "clusterIP", None)
                    if cluster_ip:
                        doc.setdefault("spec", {})["clusterIP"] = cluster_ip
                resource.replace(body=doc, namespace=namespace, name=name)
            else:
                resource.create(body=doc, namespace=namespace)
        except Exception as e:
            return False, f"{kind} {name}: {e!s}"
    return True, "Manifest applied to cluster"


@router.post("/apply")
def apply_deployment_to_cluster(
    req: DeployApplyRequest,
    _=Depends(require_auth)
):
    """
    Generate Kubernetes manifest for the agent and, when the control-plane runs in-cluster,
    apply it to the current cluster. Always records the deployment in the deployment registry.
    
    When not in-cluster, returns the manifest YAML so the user can apply via kubectl or the GKE deploy tab.
    """
    if req.deployment_type not in ("gke", "aks", "eks"):
        raise HTTPException(status_code=400, detail="deployment_type must be gke, aks, or eks")
    manifest = generate_manifest(
        req.deployment_type,
        req.agent_id,
        req.image_url,
        namespace=req.namespace,
        replicas=req.replicas,
        port=req.port,
        control_plane_url=req.control_plane_url,
        llm_config=req.llm_config,  # Runtime LLM configuration
    )
    manifest_yaml = manifest_to_yaml(manifest)
    applied = False
    message = ""
    if _running_in_cluster():
        applied, message = _apply_manifest_in_cluster(manifest_yaml)
        if not applied:
            raise HTTPException(status_code=502, detail=f"Failed to apply manifest: {message}")
    else:
        message = "Not in-cluster; apply the manifest manually (kubectl apply -f) or use the Deploy Agent tab with gcloud."
    endpoint = f"http://{_k8s_safe_name(req.agent_id)}.{req.namespace}.svc.cluster.local:{req.port}"
    save_deployment(
        req.agent_id,
        req.environment,
        req.deployment_type,
        "deployed",
        endpoint,
        {
            "image_url": req.image_url,
            "namespace": req.namespace,
            "replicas": req.replicas,
            "port": req.port,
            "control_plane_url": req.control_plane_url,
            "applied_in_cluster": applied,
        },
    )
    return {
        "success": True,
        "applied": applied,
        "message": message,
        "manifest_yaml": None if applied else manifest_yaml,
        "deployment": load_deployment(req.agent_id, req.environment),
    }


@router.get("/environments")
def list_deployment_environments(_=Depends(require_auth)):
    """List all environments that have deployments."""
    return {"environments": list_environments()}


class DeploymentChatRequest(BaseModel):
    """Request to send a chat message to a deployed agent (proxied via control-plane)."""
    agent_id: str
    environment: str
    message: str


@router.post("/chat")
def deployment_chat(
    req: DeploymentChatRequest,
    _=Depends(require_auth)
):
    """
    Send a message to a deployed agent. Control-plane proxies the request to the
    deployment endpoint (e.g. in-cluster service). Agent must expose POST /invoke
    with body {"query": "..."} and return {"response": "..."}.
    """
    deployment = load_deployment(req.agent_id, req.environment)
    if not deployment:
        raise HTTPException(
            status_code=404,
            detail=f"Deployment not found: {req.agent_id} in {req.environment}"
        )
    endpoint = (deployment.get("endpoint") or "").rstrip("/")
    if not endpoint:
        raise HTTPException(
            status_code=400,
            detail="Deployment has no endpoint; cannot send message"
        )
    url = f"{endpoint}/invoke"
    try:
        r = requests_lib.post(
            url,
            json={"query": req.message},
            timeout=30,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
        return {"response": data.get("response", ""), "error": data.get("error")}
    except requests_lib.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Agent request failed: {e!s}"
        )


@router.get("")
def list_all_deployments(
    environment: Optional[str] = None,
    agent_id: Optional[str] = None,
    _=Depends(require_auth)
):
    """
    List all deployments, optionally filtered by environment or agent_id.
    
    Args:
        environment: Optional environment filter
        agent_id: Optional agent_id filter
    """
    if agent_id:
        deployments = get_deployments_for_agent(agent_id)
    else:
        deployments = list_deployments(environment)
    
    return {"deployments": deployments}


@router.get("/{agent_id}")
def get_agent_deployments(agent_id: str, _=Depends(require_auth)):
    """Get all deployments for a specific agent."""
    deployments = get_deployments_for_agent(agent_id)
    return {"agent_id": agent_id, "deployments": deployments}


@router.get("/{agent_id}/{environment}")
def get_deployment(
    agent_id: str,
    environment: str,
    _=Depends(require_auth)
):
    """Get deployment record for an agent in an environment."""
    deployment = load_deployment(agent_id, environment)
    if not deployment:
        raise HTTPException(
            status_code=404,
            detail=f"Deployment not found: {agent_id} in {environment}"
        )
    return deployment


@router.post("")
def create_deployment(
    deployment: DeploymentRequest,
    _=Depends(require_auth)
):
    """Create or update a deployment record."""
    metadata = dict(deployment.metadata or {})
    if deployment.image_url is not None:
        metadata["image_url"] = deployment.image_url
    save_deployment(
        deployment.agent_id,
        deployment.environment,
        deployment.deployment_type,
        deployment.status,
        deployment.endpoint,
        metadata
    )
    
    return {
        "message": f"Deployment recorded for {deployment.agent_id} in {deployment.environment}",
        "deployment": load_deployment(deployment.agent_id, deployment.environment)
    }


@router.put("/{agent_id}/{environment}")
def update_deployment(
    agent_id: str,
    environment: str,
    status: Optional[str] = None,
    endpoint: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    _=Depends(require_auth)
):
    """Update deployment status or metadata."""
    existing = load_deployment(agent_id, environment)
    if not existing:
        raise HTTPException(
            status_code=404,
            detail=f"Deployment not found: {agent_id} in {environment}"
        )
    
    # Update fields
    if status:
        existing["status"] = status
    if endpoint:
        existing["endpoint"] = endpoint
    if metadata:
        existing.update(metadata)
    
    save_deployment(
        agent_id,
        environment,
        existing.get("deployment_type", "unknown"),
        existing.get("status", "unknown"),
        existing.get("endpoint"),
        existing
    )
    
    return {
        "message": f"Deployment updated for {agent_id} in {environment}",
        "deployment": load_deployment(agent_id, environment)
    }


@router.delete("/{agent_id}/{environment}")
def remove_deployment(
    agent_id: str,
    environment: str,
    _=Depends(require_auth)
):
    """Delete a deployment record."""
    if not delete_deployment(agent_id, environment):
        raise HTTPException(
            status_code=404,
            detail=f"Deployment not found: {agent_id} in {environment}"
        )
    return {"message": f"Deployment removed for {agent_id} in {environment}"}
