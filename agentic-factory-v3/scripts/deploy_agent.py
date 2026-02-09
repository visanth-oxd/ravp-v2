#!/usr/bin/env python3
"""
Deploy an agent locally (Docker) or to GKE (Kubernetes).

Usage:
    # Local Docker deployment
    python scripts/deploy_agent.py --agent payment_failed --target local --port 8080

    # GKE deployment
    python scripts/deploy_agent.py --agent payment_failed --target gke --project my-project --cluster my-cluster
"""

import argparse
import subprocess
import sys
from pathlib import Path
import yaml
import json

repo_root = Path(__file__).resolve().parent.parent


def load_agent_definition(agent_id: str) -> dict:
    """Load agent definition from config."""
    config_file = repo_root / "config" / "agents" / f"{agent_id}.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Agent definition not found: {config_file}")
    
    with open(config_file, "r") as f:
        return yaml.safe_load(f)


def generate_dockerfile(agent_id: str, control_plane_url: str = "http://localhost:8010") -> str:
    """Generate Dockerfile for agent."""
    return f"""FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agents/{agent_id}/ ./agents/{agent_id}/
COPY agent-sdk/ ./agent-sdk/
COPY config/ ./config/

# Set environment variables
ENV CONTROL_PLANE_URL={control_plane_url}
ENV PYTHONPATH=/app

# Expose port (default 8080)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run agent
CMD ["python", "-m", "agents.{agent_id}.agent"]
"""


def deploy_local(agent_id: str, port: int = 8080, image_tag: str = "latest", control_plane_url: str = "http://localhost:8010"):
    """Deploy agent locally using Docker."""
    print(f"🐳 Deploying {agent_id} locally...")
    
    # Load agent definition
    agent_def = load_agent_definition(agent_id)
    print(f"✓ Loaded agent definition: {agent_def.get('agent_id')} v{agent_def.get('version', '1.0.0')}")
    
    # Generate Dockerfile
    dockerfile_content = generate_dockerfile(agent_id, control_plane_url)
    dockerfile_path = repo_root / f"Dockerfile.{agent_id}"
    
    print(f"📝 Writing Dockerfile to {dockerfile_path}")
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile_content)
    
    # Build image
    image_name = f"agent-{agent_id.lower()}"
    full_image = f"{image_name}:{image_tag}"
    
    print(f"🔨 Building Docker image: {full_image}")
    build_cmd = ["docker", "build", "-t", full_image, "-f", str(dockerfile_path), str(repo_root)]
    
    result = subprocess.run(build_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Docker build failed: {result.stderr}")
        return False
    
    print(f"✓ Image built successfully")
    
    # Stop existing container if running
    print(f"🛑 Stopping existing container (if any)...")
    subprocess.run(["docker", "stop", agent_id], capture_output=True)
    subprocess.run(["docker", "rm", agent_id], capture_output=True)
    
    # Run container
    print(f"🚀 Starting container on port {port}...")
    run_cmd = [
        "docker", "run", "-d",
        "--name", agent_id,
        "-p", f"{port}:8080",
        "-e", f"CONTROL_PLANE_URL={control_plane_url}",
        "-e", "GOOGLE_API_KEY",
        full_image
    ]
    
    result = subprocess.run(run_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Docker run failed: {result.stderr}")
        return False
    
    print(f"✅ Agent {agent_id} deployed successfully!")
    print(f"   Container: {agent_id}")
    print(f"   Port: http://localhost:{port}")
    print(f"   Logs: docker logs -f {agent_id}")
    
    return True


def generate_k8s_manifest(agent_id: str, project: str, cluster: str, namespace: str = "agents",
                         replicas: int = 1, port: int = 8080, control_plane_url: str = "http://control-plane:8010"):
    """Generate Kubernetes deployment manifest."""
    image_name = f"gcr.io/{project}/agent-{agent_id.lower()}:latest"
    
    manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": agent_id,
            "namespace": namespace,
            "labels": {
                "app": agent_id,
                "component": "agent"
            }
        },
        "spec": {
            "replicas": replicas,
            "selector": {
                "matchLabels": {
                    "app": agent_id
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": agent_id
                    }
                },
                "spec": {
                    "containers": [{
                        "name": agent_id,
                        "image": image_name,
                        "ports": [{
                            "containerPort": port
                        }],
                        "env": [
                            {
                                "name": "CONTROL_PLANE_URL",
                                "value": control_plane_url
                            },
                            {
                                "name": "GOOGLE_API_KEY",
                                "valueFrom": {
                                    "secretKeyRef": {
                                        "name": "agent-secrets",
                                        "key": "google-api-key"
                                    }
                                }
                            }
                        ],
                        "resources": {
                            "requests": {
                                "cpu": "100m",
                                "memory": "256Mi"
                            },
                            "limits": {
                                "cpu": "500m",
                                "memory": "512Mi"
                            }
                        },
                        "livenessProbe": {
                            "httpGet": {
                                "path": "/health",
                                "port": port
                            },
                            "initialDelaySeconds": 30,
                            "periodSeconds": 10
                        },
                        "readinessProbe": {
                            "httpGet": {
                                "path": "/health",
                                "port": port
                            },
                            "initialDelaySeconds": 10,
                            "periodSeconds": 5
                        }
                    }]
                }
            }
        }
    }
    
    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": agent_id,
            "namespace": namespace,
            "labels": {
                "app": agent_id
            }
        },
        "spec": {
            "type": "ClusterIP",
            "ports": [{
                "port": 80,
                "targetPort": port,
                "protocol": "TCP"
            }],
            "selector": {
                "app": agent_id
            }
        }
    }
    
    return manifest, service


def deploy_gke(agent_id: str, project: str, cluster: str, namespace: str = "agents",
               replicas: int = 1, port: int = 8080, control_plane_url: str = "http://control-plane:8010",
               build_image: bool = True):
    """Deploy agent to GKE."""
    print(f"☸️  Deploying {agent_id} to GKE...")
    print(f"   Project: {project}")
    print(f"   Cluster: {cluster}")
    print(f"   Namespace: {namespace}")
    
    # Load agent definition
    agent_def = load_agent_definition(agent_id)
    print(f"✓ Loaded agent definition: {agent_def.get('agent_id')} v{agent_def.get('version', '1.0.0')}")
    
    # Generate Dockerfile
    dockerfile_content = generate_dockerfile(agent_id, control_plane_url)
    dockerfile_path = repo_root / f"Dockerfile.{agent_id}"
    
    print(f"📝 Writing Dockerfile to {dockerfile_path}")
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile_content)
    
    # Build and push image
    image_name = f"gcr.io/{project}/agent-{agent_id.lower()}"
    
    if build_image:
        print(f"🔨 Building Docker image: {image_name}")
        build_cmd = ["docker", "build", "-t", f"{image_name}:latest", "-f", str(dockerfile_path), str(repo_root)]
        
        result = subprocess.run(build_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Docker build failed: {result.stderr}")
            return False
        
        print(f"📤 Pushing image to GCR...")
        push_cmd = ["docker", "push", f"{image_name}:latest"]
        
        result = subprocess.run(push_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Docker push failed: {result.stderr}")
            print(f"   Make sure you're authenticated: gcloud auth configure-docker")
            return False
        
        print(f"✓ Image pushed successfully")
    
    # Generate Kubernetes manifests
    deployment, service = generate_k8s_manifest(agent_id, project, cluster, namespace, replicas, port, control_plane_url)
    
    manifest_path = repo_root / f"{agent_id}-deployment.yaml"
    print(f"📝 Writing Kubernetes manifest to {manifest_path}")
    
    with open(manifest_path, "w") as f:
        yaml.dump(deployment, f, default_flow_style=False, sort_keys=False)
        f.write("---\n")
        yaml.dump(service, f, default_flow_style=False, sort_keys=False)
    
    # Set GCP project and get cluster credentials
    print(f"🔧 Configuring GCP...")
    subprocess.run(["gcloud", "config", "set", "project", project], check=True)
    subprocess.run(["gcloud", "container", "clusters", "get-credentials", cluster], check=True)
    
    # Create namespace if not exists
    print(f"📦 Creating namespace {namespace}...")
    subprocess.run([
        "kubectl", "create", "namespace", namespace, "--dry-run=client", "-o", "yaml"
    ], stdout=subprocess.PIPE)
    subprocess.run([
        "kubectl", "apply", "-f", "-"
    ], input=subprocess.PIPE, check=False)
    
    # Apply deployment
    print(f"🚀 Deploying to GKE...")
    apply_cmd = ["kubectl", "apply", "-f", str(manifest_path)]
    
    result = subprocess.run(apply_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Deployment failed: {result.stderr}")
        return False
    
    print(f"✅ Agent {agent_id} deployed to GKE successfully!")
    print(f"   Namespace: {namespace}")
    print(f"   Deployment: {agent_id}")
    print(f"   Service: {agent_id}")
    print(f"   Check status: kubectl get pods -n {namespace} -l app={agent_id}")
    print(f"   View logs: kubectl logs -n {namespace} -l app={agent_id} --tail=50")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Deploy an agent")
    parser.add_argument("--agent", required=True, help="Agent ID to deploy")
    parser.add_argument("--target", required=True, choices=["local", "gke"], help="Deployment target")
    
    # Local deployment options
    parser.add_argument("--port", type=int, default=8080, help="Port for local deployment")
    parser.add_argument("--tag", default="latest", help="Docker image tag")
    parser.add_argument("--control-plane-url", default="http://localhost:8010", help="Control plane URL")
    
    # GKE deployment options
    parser.add_argument("--project", help="GCP project ID (required for GKE)")
    parser.add_argument("--cluster", help="GKE cluster name (required for GKE)")
    parser.add_argument("--namespace", default="agents", help="Kubernetes namespace")
    parser.add_argument("--replicas", type=int, default=1, help="Number of replicas")
    parser.add_argument("--no-build", action="store_true", help="Skip Docker build/push (use existing image)")
    
    args = parser.parse_args()
    
    if args.target == "local":
        success = deploy_local(args.agent, args.port, args.tag, args.control_plane_url)
    elif args.target == "gke":
        if not args.project or not args.cluster:
            parser.error("--project and --cluster are required for GKE deployment")
        success = deploy_gke(
            args.agent,
            args.project,
            args.cluster,
            args.namespace,
            args.replicas,
            args.port,
            args.control_plane_url,
            build_image=not args.no_build
        )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
