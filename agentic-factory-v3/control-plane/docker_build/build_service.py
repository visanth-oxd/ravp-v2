"""Docker build and push service for agent deployments."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import json


def is_docker_available() -> Tuple[bool, str]:
    """
    Check if Docker daemon is running and accessible.
    
    Returns:
        (available, message) - True if docker info succeeds, else False with error message
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, "Docker is available"
        return False, result.stderr.strip() or "Docker daemon not running"
    except FileNotFoundError:
        return False, "Docker is not installed or not in PATH"
    except subprocess.TimeoutExpired:
        return False, "Docker daemon did not respond (timeout)"
    except Exception as e:
        return False, str(e)


def get_repo_root() -> Path:
    """Get repository root directory."""
    # Path: control-plane/docker_build/build_service.py
    # Go up: build_service.py -> docker_build -> control-plane -> repo root
    return Path(__file__).resolve().parent.parent.parent


def detect_registry_type(registry_url: str) -> str:
    """
    Detect registry type from URL.
    
    Returns: "gcr", "acr", "ecr", "dockerhub", or "unknown"
    """
    url_lower = registry_url.lower()
    if "gcr.io" in url_lower or "pkg.dev" in url_lower:
        return "gcr"
    elif ".azurecr.io" in url_lower:
        return "acr"
    elif ".ecr." in url_lower and ".amazonaws.com" in url_lower:
        return "ecr"
    elif "docker.io" in url_lower or "hub.docker.com" in url_lower or not "/" in url_lower.split("://")[-1].split(":")[0]:
        return "dockerhub"
    else:
        return "unknown"


def _check_cmd(name: str) -> bool:
    """Return True if command is available on PATH."""
    return shutil.which(name) is not None


# Common install locations for gcloud (control plane often runs without full shell PATH)
_GCLOUD_CANDIDATES = [
    "/opt/homebrew/share/google-cloud-sdk/bin/gcloud",   # macOS Homebrew (Apple Silicon)
    "/usr/local/share/google-cloud-sdk/bin/gcloud",       # macOS Homebrew (Intel) / Linux
    os.path.expanduser("~/google-cloud-sdk/bin/gcloud"),  # User install script
    "/usr/bin/gcloud",                                    # Linux package
]


def _find_gcloud() -> Optional[str]:
    """Return path to gcloud executable, from PATH or common install locations."""
    path = shutil.which("gcloud")
    if path:
        return path
    for candidate in _GCLOUD_CANDIDATES:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _gcloud_cmd_and_env(gcloud_bin: str, args):
    """
    Return (cmd_list, env_dict) to run gcloud with given args.
    If the SDK has no lib/gcloud.py (e.g. Homebrew layout), run via python -m googlecloudsdk.gcloud_main.
    """
    sdk_root = os.path.dirname(os.path.dirname(gcloud_bin))
    lib_gcloud_py = os.path.join(sdk_root, "lib", "gcloud.py")
    if os.path.isfile(lib_gcloud_py):
        return [gcloud_bin] + list(args), None
    # Homebrew/newer layout: lib/gcloud.py missing, use python -m
    lib_dir = os.path.join(sdk_root, "lib")
    if os.path.isdir(lib_dir) and os.path.isdir(os.path.join(lib_dir, "googlecloudsdk")):
        env = os.environ.copy()
        env["PYTHONPATH"] = lib_dir + os.pathsep + env.get("PYTHONPATH", "")
        env["CLOUDSDK_ROOT_DIR"] = sdk_root
        return [sys.executable, "-m", "googlecloudsdk.gcloud_main"] + list(args), env
    return [gcloud_bin] + list(args), None


def authenticate_registry(registry_type: str, registry_url: str, credentials: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    """
    Authenticate with container registry.
    
    Args:
        registry_type: Type of registry (gcr, acr, ecr, dockerhub)
        registry_url: Registry URL
        credentials: Optional credentials dict
    
    Returns:
        (success, message)
    """
    try:
        if registry_type == "gcr":
            gcloud_path = _find_gcloud()
            if not gcloud_path:
                return False, (
                    "gcloud CLI is not installed or not on PATH. "
                    "Install Google Cloud SDK (https://cloud.google.com/sdk/docs/install) on the machine where the control plane runs, "
                    "then run: gcloud auth login && gcloud auth configure-docker gcr.io --quiet"
                )
            # GCR: Use gcloud auth configure-docker (handle SDKs where lib/gcloud.py is missing, e.g. Homebrew)
            gcloud_cmd, gcloud_env = _gcloud_cmd_and_env(gcloud_path, ["auth", "configure-docker", "gcr.io", "--quiet"])
            result = subprocess.run(
                gcloud_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=gcloud_env,
            )
            if result.returncode == 0:
                return True, "Authenticated with GCR"
            return False, f"GCR auth failed: {result.stderr or result.stdout}"
        
        elif registry_type == "acr":
            # ACR: Use az acr login
            registry_name = registry_url.split(".")[0].split("/")[-1]
            result = subprocess.run(
                ["az", "acr", "login", "--name", registry_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return True, "Authenticated with ACR"
            return False, f"ACR auth failed: {result.stderr}"
        
        elif registry_type == "ecr":
            # ECR: Use aws ecr get-login-password
            region = None
            if ".ecr." in registry_url:
                # Extract region from URL: account.dkr.ecr.region.amazonaws.com
                parts = registry_url.split(".ecr.")
                if len(parts) > 1:
                    region = parts[1].split(".")[0]
            
            if not region:
                return False, "Could not determine ECR region from URL"
            
            result = subprocess.run(
                ["aws", "ecr", "get-login-password", "--region", region],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                password = result.stdout.strip()
                # Login to docker
                login_result = subprocess.run(
                    ["docker", "login", "--username", "AWS", "--password-stdin", registry_url],
                    input=password,
                    text=True,
                    capture_output=True,
                    timeout=30
                )
                if login_result.returncode == 0:
                    return True, "Authenticated with ECR"
                return False, f"ECR docker login failed: {login_result.stderr}"
            return False, f"ECR auth failed: {result.stderr}"
        
        elif registry_type == "dockerhub":
            # Docker Hub: Use docker login
            username = credentials.get("username") if credentials else os.getenv("DOCKER_USERNAME")
            password = credentials.get("password") if credentials else os.getenv("DOCKER_PASSWORD")
            
            if not username or not password:
                return False, "Docker Hub credentials not provided"
            
            result = subprocess.run(
                ["docker", "login", "--username", username, "--password", password],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return True, "Authenticated with Docker Hub"
            return False, f"Docker Hub auth failed: {result.stderr}"
        
        else:
            return False, f"Unknown registry type: {registry_type}"
    
    except subprocess.TimeoutExpired:
        return False, "Authentication timeout"
    except FileNotFoundError as e:
        cmd = str(e).split(":")[-1].strip() if ":" in str(e) else "required CLI"
        return False, (
            f"Command not found: {cmd}. For GCR install Google Cloud SDK (https://cloud.google.com/sdk/docs/install) "
            "on the machine where the control plane runs, then run: gcloud auth login && gcloud auth configure-docker gcr.io --quiet"
        )
    except Exception as e:
        return False, f"Authentication error: {str(e)}"


def generate_dockerfile_content(agent_id: str, control_plane_url: str = "http://localhost:8010") -> str:
    """
    Generate Dockerfile content for an agent.
    This is the single source of truth for in-cluster (Kaniko) builds: the API does not
    use repo Dockerfile.{agent_id}; the Kaniko job gets this content via a ConfigMap.
    Uses scripts/run_agent_server.py so the container starts uvicorn reliably (no runpy).
    """
    return f"""FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code, tools, synthetic data, and server runner
COPY agents/{agent_id}/ ./agents/{agent_id}/
COPY agent-sdk/ ./agent-sdk/
COPY config/ ./config/
COPY tools/ ./tools/
COPY data/ ./data/
COPY scripts/run_agent_server.py ./scripts/

# Set environment variables
ENV CONTROL_PLANE_URL={control_plane_url}
ENV PYTHONPATH=/app

# Expose port (default 8080)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run agent (wrapper forces __main__ so uvicorn server starts)
CMD ["python", "scripts/run_agent_server.py", "{agent_id}"]
"""


def _ensure_dockerfile(repo_root: Path, agent_id: str, control_plane_url: str = "http://localhost:8010") -> Path:
    """
    Ensure a Dockerfile exists for the agent: use existing Dockerfile.{agent_id}
    or generate one and write it to repo_root.
    """
    agent_dir = repo_root / "agents" / agent_id
    if not agent_dir.is_dir():
        raise FileNotFoundError(
            f"Agent directory not found: {agent_dir}. "
            f"Ensure agents/{agent_id}/ exists with agent code."
        )
    dockerfile_path = repo_root / f"Dockerfile.{agent_id}"
    if not dockerfile_path.exists():
        content = generate_dockerfile_content(agent_id, control_plane_url)
        dockerfile_path.write_text(content, encoding="utf-8")
    return dockerfile_path


def build_docker_image(
    agent_id: str,
    dockerfile_path: Optional[Path] = None,
    tag: str = "latest",
    build_args: Optional[Dict[str, str]] = None,
    context_path: Optional[Path] = None,
    control_plane_url: str = "http://localhost:8010",
) -> Tuple[bool, str, str]:
    """
    Build Docker image for an agent.
    
    If Dockerfile.{agent_id} does not exist, it is generated automatically
    (same content as scripts/deploy_agent.py).
    
    Args:
        agent_id: Agent identifier
        dockerfile_path: Path to Dockerfile (defaults to repo_root/Dockerfile.{agent_id})
        tag: Image tag
        build_args: Optional build arguments
        context_path: Build context path (defaults to repo root)
        control_plane_url: Used when generating Dockerfile
    
    Returns:
        (success, image_name, error_message)
    """
    repo_root = get_repo_root()
    
    if not context_path:
        context_path = repo_root
    
    if not dockerfile_path:
        dockerfile_path = repo_root / f"Dockerfile.{agent_id}"
    
    # If Dockerfile doesn't exist, generate it
    if not dockerfile_path.exists():
        try:
            control_plane_url = (build_args or {}).get("CONTROL_PLANE_URL") or control_plane_url
            dockerfile_path = _ensure_dockerfile(repo_root, agent_id, control_plane_url)
        except FileNotFoundError as e:
            return False, "", str(e)
    
    image_name = f"agent-{agent_id.lower()}:{tag}"
    
    # Build command
    cmd = ["docker", "build", "-t", image_name, "-f", str(dockerfile_path), str(context_path)]
    
    # Add build args
    if build_args:
        for key, value in build_args.items():
            cmd.extend(["--build-arg", f"{key}={value}"])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode == 0:
            return True, image_name, ""
        else:
            return False, "", f"Build failed: {result.stderr}"
    
    except subprocess.TimeoutExpired:
        return False, "", "Build timeout (exceeded 10 minutes)"
    except Exception as e:
        return False, "", f"Build error: {str(e)}"


def push_docker_image(
    image_name: str,
    registry_url: str,
    registry_type: Optional[str] = None,
    credentials: Optional[Dict[str, str]] = None
) -> Tuple[bool, str, str]:
    """
    Tag and push Docker image to registry.
    
    Args:
        image_name: Local image name (e.g., "agent-payment_failed:latest")
        registry_url: Full registry URL (e.g., "gcr.io/my-project/agent-payment_failed:latest")
        registry_type: Optional registry type (auto-detected if not provided)
        credentials: Optional credentials for authentication
    
    Returns:
        (success, pushed_image_url, error_message)
    """
    if not registry_type:
        registry_type = detect_registry_type(registry_url)
    
    # Authenticate first
    auth_success, auth_msg = authenticate_registry(registry_type, registry_url, credentials)
    if not auth_success:
        return False, "", f"Authentication failed: {auth_msg}"
    
    # Tag image
    tag_result = subprocess.run(
        ["docker", "tag", image_name, registry_url],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if tag_result.returncode != 0:
        return False, "", f"Tag failed: {tag_result.stderr}"
    
    # Push image
    try:
        push_result = subprocess.run(
            ["docker", "push", registry_url],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if push_result.returncode == 0:
            return True, registry_url, ""
        else:
            return False, "", f"Push failed: {push_result.stderr}"
    
    except subprocess.TimeoutExpired:
        return False, "", "Push timeout (exceeded 10 minutes)"
    except Exception as e:
        return False, "", f"Push error: {str(e)}"


def build_and_push(
    agent_id: str,
    registry_url: str,
    tag: str = "latest",
    dockerfile_path: Optional[Path] = None,
    build_args: Optional[Dict[str, str]] = None,
    credentials: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Complete workflow: build Docker image and push to registry.
    
    Args:
        agent_id: Agent identifier
        registry_url: Full registry URL for the image
        tag: Image tag
        dockerfile_path: Optional path to Dockerfile
        build_args: Optional build arguments
        credentials: Optional registry credentials
    
    Returns:
        Dict with success, image_url, and messages
    """
    result = {
        "success": False,
        "image_url": "",
        "steps": [],
        "error": ""
    }
    
    # Check Docker is available before starting
    docker_ok, docker_msg = is_docker_available()
    if not docker_ok:
        result["error"] = (
            f"Docker is not available: {docker_msg}. "
            "Start Docker Desktop (or the Docker daemon) on this machine, or build images in CI/CD instead."
        )
        return result
    
    # Step 1: Build
    result["steps"].append({"step": "build", "status": "in_progress"})
    build_success, local_image, build_error = build_docker_image(
        agent_id, dockerfile_path, tag, build_args
    )
    
    if not build_success:
        result["steps"][-1]["status"] = "failed"
        result["error"] = build_error
        return result
    
    result["steps"][-1]["status"] = "completed"
    result["steps"][-1]["message"] = f"Built image: {local_image}"
    
    # Step 2: Push
    result["steps"].append({"step": "push", "status": "in_progress"})
    registry_type = detect_registry_type(registry_url)
    push_success, pushed_url, push_error = push_docker_image(
        local_image, registry_url, registry_type, credentials
    )
    
    if not push_success:
        result["steps"][-1]["status"] = "failed"
        result["error"] = push_error
        return result
    
    result["steps"][-1]["status"] = "completed"
    result["steps"][-1]["message"] = f"Pushed to: {pushed_url}"
    
    result["success"] = True
    result["image_url"] = pushed_url
    
    return result
