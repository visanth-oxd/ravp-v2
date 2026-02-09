#!/usr/bin/env python3
"""
Generate Kubernetes deployment manifests for agents.

Usage:
    python scripts/generate_deployment_manifest.py --agent payment_failed --project my-project --output k8s/
"""

import argparse
import yaml
from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parent.parent


def load_agent_definition(agent_id: str) -> dict:
    """Load agent definition from config."""
    config_file = repo_root / "config" / "agents" / f"{agent_id}.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Agent definition not found: {config_file}")
    
    import yaml
    with open(config_file, "r") as f:
        return yaml.safe_load(f)


def generate_deployment_manifest(agent_id: str, project: str, namespace: str = "agents",
                                 replicas: int = 1, port: int = 8080,
                                 control_plane_url: str = "http://control-plane:8010",
                                 cpu_request: str = "100m", memory_request: str = "256Mi",
                                 cpu_limit: str = "500m", memory_limit: str = "512Mi"):
    """Generate Kubernetes Deployment manifest."""
    image_name = f"gcr.io/{project}/agent-{agent_id.lower()}:latest"
    
    deployment = {
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
                            "containerPort": port,
                            "name": "http"
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
                                "cpu": cpu_request,
                                "memory": memory_request
                            },
                            "limits": {
                                "cpu": cpu_limit,
                                "memory": memory_limit
                            }
                        },
                        "livenessProbe": {
                            "httpGet": {
                                "path": "/health",
                                "port": port
                            },
                            "initialDelaySeconds": 30,
                            "periodSeconds": 10,
                            "timeoutSeconds": 5,
                            "failureThreshold": 3
                        },
                        "readinessProbe": {
                            "httpGet": {
                                "path": "/health",
                                "port": port
                            },
                            "initialDelaySeconds": 10,
                            "periodSeconds": 5,
                            "timeoutSeconds": 3,
                            "failureThreshold": 3
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
                "protocol": "TCP",
                "name": "http"
            }],
            "selector": {
                "app": agent_id
            }
        }
    }
    
    return deployment, service


def main():
    parser = argparse.ArgumentParser(description="Generate Kubernetes deployment manifests")
    parser.add_argument("--agent", required=True, help="Agent ID")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--namespace", default="agents", help="Kubernetes namespace")
    parser.add_argument("--replicas", type=int, default=1, help="Number of replicas")
    parser.add_argument("--port", type=int, default=8080, help="Container port")
    parser.add_argument("--control-plane-url", default="http://control-plane:8010", help="Control plane URL")
    parser.add_argument("--output", default="k8s", help="Output directory")
    parser.add_argument("--cpu-request", default="100m", help="CPU request")
    parser.add_argument("--memory-request", default="256Mi", help="Memory request")
    parser.add_argument("--cpu-limit", default="500m", help="CPU limit")
    parser.add_argument("--memory-limit", default="512Mi", help="Memory limit")
    
    args = parser.parse_args()
    
    # Load agent definition
    try:
        agent_def = load_agent_definition(args.agent)
        print(f"✓ Loaded agent: {agent_def.get('agent_id')} v{agent_def.get('version', '1.0.0')}")
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    # Generate manifests
    deployment, service = generate_deployment_manifest(
        args.agent,
        args.project,
        args.namespace,
        args.replicas,
        args.port,
        args.control_plane_url,
        args.cpu_request,
        args.memory_request,
        args.cpu_limit,
        args.memory_limit
    )
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write deployment
    deployment_file = output_dir / f"{args.agent}-deployment.yaml"
    with open(deployment_file, "w") as f:
        yaml.dump(deployment, f, default_flow_style=False, sort_keys=False)
        f.write("---\n")
        yaml.dump(service, f, default_flow_style=False, sort_keys=False)
    
    print(f"✅ Generated manifest: {deployment_file}")
    print(f"   Deploy with: kubectl apply -f {deployment_file}")


if __name__ == "__main__":
    main()
