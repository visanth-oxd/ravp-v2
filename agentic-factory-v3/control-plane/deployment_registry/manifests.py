"""Generate Kubernetes manifests for different cloud providers."""

from typing import Dict, Any, Optional, List
import yaml


def _k8s_safe_name(agent_id: str) -> str:
    """K8s resource names must be RFC 1123 / DNS-1035: alphanumeric and '-' only."""
    return agent_id.replace("_", "-").lower()


def _build_env_vars(control_plane_url: str, llm_config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Build environment variables for agent deployment, including runtime LLM config."""
    env_vars = [
        {"name": "CONTROL_PLANE_URL", "value": control_plane_url}
    ]
    
    # Add runtime LLM configuration if provided
    if llm_config:
        # API key (can be passed directly or from secret)
        if "api_key" in llm_config:
            env_vars.append({
                "name": "GOOGLE_API_KEY",
                "value": llm_config["api_key"]
            })
        elif "api_key_secret" in llm_config:
            # Reference to Kubernetes secret
            secret_name = llm_config["api_key_secret"].get("name", "agent-secrets")
            secret_key = llm_config["api_key_secret"].get("key", "google-api-key")
            env_vars.append({
                "name": "GOOGLE_API_KEY",
                "valueFrom": {
                    "secretKeyRef": {
                        "name": secret_name,
                        "key": secret_key,
                        "optional": True
                    }
                }
            })
        else:
            # Default to secret
            env_vars.append({
                "name": "GOOGLE_API_KEY",
                "valueFrom": {
                    "secretKeyRef": {
                        "name": "agent-secrets",
                        "key": "google-api-key",
                        "optional": True
                    }
                }
            })
        
        # Custom endpoint
        if "endpoint" in llm_config:
            env_vars.append({
                "name": "GOOGLE_API_ENDPOINT",
                "value": llm_config["endpoint"]
            })
        
        # Provider override
        if "provider" in llm_config:
            env_vars.append({
                "name": "LLM_PROVIDER",
                "value": llm_config["provider"]
            })
        
        # GCP project (for Vertex AI)
        if "project" in llm_config:
            env_vars.append({
                "name": "GOOGLE_CLOUD_PROJECT",
                "value": llm_config["project"]
            })
        
        # GCP region (for Vertex AI)
        if "region" in llm_config:
            env_vars.append({
                "name": "GOOGLE_CLOUD_REGION",
                "value": llm_config["region"]
            })
        
        # OpenAI configuration
        if "openai_api_key" in llm_config:
            env_vars.append({
                "name": "OPENAI_API_KEY",
                "value": llm_config["openai_api_key"]
            })
        
        if "openai_base_url" in llm_config:
            env_vars.append({
                "name": "OPENAI_BASE_URL",
                "value": llm_config["openai_base_url"]
            })
        
        # Anthropic configuration
        if "anthropic_api_key" in llm_config:
            env_vars.append({
                "name": "ANTHROPIC_API_KEY",
                "value": llm_config["anthropic_api_key"]
            })
    else:
        # No runtime config - use default secret
        env_vars.append({
            "name": "GOOGLE_API_KEY",
            "valueFrom": {
                "secretKeyRef": {
                    "name": "agent-secrets",
                    "key": "google-api-key",
                    "optional": True
                }
            }
        })
    
    return env_vars


def generate_gke_manifest(
    agent_id: str,
    image_url: str,
    namespace: str = "agents",
    replicas: int = 1,
    port: int = 8080,
    control_plane_url: str = "http://control-plane:8010",
    cpu_request: str = "100m",
    memory_request: str = "256Mi",
    cpu_limit: str = "500m",
    memory_limit: str = "512Mi",
    llm_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate GKE (Google Kubernetes Engine) deployment manifest."""
    name = _k8s_safe_name(agent_id)
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {
                "app": name,
                "component": "agent"
            }
        },
        "spec": {
            "replicas": replicas,
            "selector": {
                "matchLabels": {
                    "app": name
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": name
                    }
                },
                "spec": {
                    "containers": [
                        {
                            "name": name,
                            "image": image_url,
                            "ports": [
                                {"containerPort": port}
                            ],
                            "env": _build_env_vars(control_plane_url, llm_config),
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
                        }
                    ]
                }
            }
        }
    }
    
    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "selector": {
                "app": name
            },
            "ports": [
                {
                    "port": port,
                    "targetPort": port
                }
            ],
            "type": "ClusterIP"
        }
    }
    
    return {"deployment": deployment, "service": service}


def generate_aks_manifest(
    agent_id: str,
    image_url: str,
    namespace: str = "agents",
    replicas: int = 1,
    port: int = 8080,
    control_plane_url: str = "http://control-plane:8010",
    cpu_request: str = "100m",
    memory_request: str = "256Mi",
    cpu_limit: str = "500m",
    memory_limit: str = "512Mi",
    llm_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate AKS (Azure Kubernetes Service) deployment manifest."""
    # AKS uses same Kubernetes manifest format as GKE
    return generate_gke_manifest(
        agent_id, image_url, namespace, replicas, port,
        control_plane_url, cpu_request, memory_request, cpu_limit, memory_limit,
        llm_config
    )


def generate_eks_manifest(
    agent_id: str,
    image_url: str,
    namespace: str = "agents",
    replicas: int = 1,
    port: int = 8080,
    control_plane_url: str = "http://control-plane:8010",
    cpu_request: str = "100m",
    memory_request: str = "256Mi",
    cpu_limit: str = "500m",
    memory_limit: str = "512Mi",
    llm_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate EKS (Amazon Elastic Kubernetes Service) deployment manifest."""
    # EKS uses same Kubernetes manifest format as GKE
    return generate_gke_manifest(
        agent_id, image_url, namespace, replicas, port,
        control_plane_url, cpu_request, memory_request, cpu_limit, memory_limit,
        llm_config
    )


def generate_manifest(
    deployment_type: str,
    agent_id: str,
    image_url: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate deployment manifest based on deployment type.
    
    Args:
        deployment_type: "gke", "aks", "eks"
        agent_id: Agent identifier
        image_url: Container image URL
        **kwargs: Additional parameters (namespace, replicas, etc.)
    
    Returns:
        Dict with "deployment" and "service" manifests
    """
    if deployment_type == "gke":
        return generate_gke_manifest(agent_id, image_url, **kwargs)
    elif deployment_type == "aks":
        return generate_aks_manifest(agent_id, image_url, **kwargs)
    elif deployment_type == "eks":
        return generate_eks_manifest(agent_id, image_url, **kwargs)
    else:
        raise ValueError(f"Unsupported deployment type: {deployment_type}")


def manifest_to_yaml(manifest: Dict[str, Any]) -> str:
    """Convert manifest dict to YAML string."""
    deployment_yaml = yaml.dump(manifest["deployment"], default_flow_style=False, sort_keys=False)
    service_yaml = yaml.dump(manifest["service"], default_flow_style=False, sort_keys=False)
    return f"{deployment_yaml}---\n{service_yaml}"
