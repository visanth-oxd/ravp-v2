"""GKE deploy API: apply manifest to GKE. Uses in-cluster K8s API when running in a pod, else gcloud + kubectl."""

import os
import shutil
import subprocess
import sys
import tempfile
import yaml
from pathlib import Path
from typing import Optional, List, Tuple
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from .auth import require_auth

router = APIRouter(prefix="/api/v2/gke", tags=["gke-deploy"])


def _running_in_cluster() -> bool:
    """True if we are inside a Kubernetes pod (in-cluster config available)."""
    return os.environ.get("KUBERNETES_SERVICE_HOST") not in (None, "")


def _apply_manifest_in_cluster(manifest_yaml: str) -> Tuple[bool, str]:
    """Apply the given YAML manifest using the Kubernetes API (in-cluster).
    Creates or replaces resources so redeploy does not conflict. Returns (success, message)."""
    try:
        from kubernetes import client, config
        from kubernetes.dynamic import DynamicClient
    except ImportError:
        return False, "kubernetes package not installed. Add kubernetes>=28.0.0 to requirements."
    try:
        config.load_incluster_config()
    except Exception as e:
        return False, f"Failed to load in-cluster config: {e}"
    k8s_client = client.ApiClient()
    dyn = DynamicClient(k8s_client)
    kind_to_resource = {"Deployment": ("apps/v1", "deployments"), "Service": ("v1", "services")}
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
                emeta = getattr(existing, "metadata", None) or (existing if isinstance(existing, dict) else {}).get("metadata", {})
                rv = emeta.get("resourceVersion") if isinstance(emeta, dict) else getattr(emeta, "resourceVersion", None)
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
    return True, "Manifest applied to current cluster (in-cluster)"

# Common gcloud install locations (control plane may run without full shell PATH)
_GCLOUD_CANDIDATES = [
    "/opt/homebrew/share/google-cloud-sdk/bin/gcloud",
    "/usr/local/share/google-cloud-sdk/bin/gcloud",
    os.path.expanduser("~/google-cloud-sdk/bin/gcloud"),
    "/usr/bin/gcloud",
]


def _find_gcloud() -> Optional[str]:
    path = shutil.which("gcloud")
    if path:
        return path
    for c in _GCLOUD_CANDIDATES:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def _gcloud_cmd_and_env(gcloud_bin: str, args: List[str]) -> Tuple[List[str], Optional[dict]]:
    """Return (cmd_list, env) to run gcloud; use python -m when lib/gcloud.py is missing (Homebrew layout)."""
    sdk_root = os.path.dirname(os.path.dirname(gcloud_bin))
    lib_gcloud_py = os.path.join(sdk_root, "lib", "gcloud.py")
    if os.path.isfile(lib_gcloud_py):
        return [gcloud_bin] + args, None
    lib_dir = os.path.join(sdk_root, "lib")
    if os.path.isdir(lib_dir) and os.path.isdir(os.path.join(lib_dir, "googlecloudsdk")):
        env = os.environ.copy()
        env["PYTHONPATH"] = lib_dir + os.pathsep + env.get("PYTHONPATH", "")
        env["CLOUDSDK_ROOT_DIR"] = sdk_root
        return [sys.executable, "-m", "googlecloudsdk.gcloud_main"] + args, env
    return [gcloud_bin] + args, None


class GkeDeployRequest(BaseModel):
    gcp_project: Optional[str] = None  # Required when not in-cluster
    gke_cluster: Optional[str] = None  # Required when not in-cluster
    gke_location: Optional[str] = None  # region (e.g. us-central1) or zone (e.g. us-central1-a)
    manifest_yaml: str  # Full Kubernetes YAML (Deployment + Service, etc.) to apply


@router.post("/deploy")
def deploy_to_gke(req: GkeDeployRequest, _=Depends(require_auth)):
    """
    Apply the given manifest to a GKE cluster.
    - When the control-plane runs **inside** a Kubernetes cluster (e.g. GKE): uses the in-cluster
      K8s API to apply the manifest to the **current** cluster. No gcloud/kubectl needed.
    - When run outside (e.g. laptop): uses gcloud + kubectl; gcp_project and gke_cluster required.
    """
    if not (req.manifest_yaml or req.manifest_yaml.strip()):
        raise HTTPException(status_code=400, detail="manifest_yaml is required")

    # When running in-cluster (e.g. control-plane pod in GKE), apply via K8s API
    if _running_in_cluster():
        success, message = _apply_manifest_in_cluster(req.manifest_yaml)
        if success:
            return {"success": True, "message": message, "stdout": message}
        raise HTTPException(status_code=502, detail=message)

    # Outside cluster: need gcloud + kubectl and project/cluster
    if not _running_in_cluster() and (not req.gcp_project or not req.gke_cluster):
        raise HTTPException(status_code=400, detail="gcp_project and gke_cluster are required when not running in-cluster")

    gcloud_path = _find_gcloud()
    if not gcloud_path:
        raise HTTPException(
            status_code=503,
            detail="gcloud not found. Install Google Cloud SDK on the control plane host (https://cloud.google.com/sdk/docs/install).",
        )

    def run_gcloud(args: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        cmd, env = _gcloud_cmd_and_env(gcloud_path, args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)

    try:
        # 1. Set GCP project
        r = run_gcloud(["config", "set", "project", req.gcp_project])
        if r.returncode != 0:
            raise HTTPException(
                status_code=502,
                detail=f"gcloud set project failed: {r.stderr or r.stdout}",
            )

        # 2. Get cluster credentials
        get_creds_args = ["container", "clusters", "get-credentials", req.gke_cluster]
        if req.gke_location:
            get_creds_args.extend(["--location", req.gke_location])
        r = run_gcloud(get_creds_args, timeout=60)
        if r.returncode != 0:
            raise HTTPException(
                status_code=502,
                detail=f"gcloud get-credentials failed: {r.stderr or r.stdout}",
            )

        # 3. Apply manifest (write to temp file so we can pass to kubectl)
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
            prefix="gke-deploy-",
        ) as f:
            f.write(req.manifest_yaml)
            path = f.name
        try:
            r = subprocess.run(
                ["kubectl", "apply", "-f", path],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if r.returncode != 0:
                raise HTTPException(
                    status_code=502,
                    detail=f"kubectl apply failed: {r.stderr or r.stdout}",
                )
        finally:
            Path(path).unlink(missing_ok=True)

        return {
            "success": True,
            "message": f"Manifest applied to cluster {req.gke_cluster}",
            "stdout": r.stdout,
        }
    except HTTPException:
        raise
    except subprocess.TimeoutExpired as e:
        raise HTTPException(status_code=504, detail=f"Deploy timed out: {e}")
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail="gcloud or kubectl not found; install Google Cloud SDK and kubectl on the control plane host",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
