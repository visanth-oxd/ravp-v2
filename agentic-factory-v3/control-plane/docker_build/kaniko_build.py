"""
Build agent Docker images in-cluster using a Kaniko Job.

When the control-plane runs inside Kubernetes and the registry is Artifact Registry,
we create a Job that: (1) copies build context from the control-plane image into a PVC,
(2) runs Kaniko to build and push the image. No Docker daemon required.
"""

import os
import time
import uuid
from typing import Optional, Tuple

from .build_service import generate_dockerfile_content


def _running_in_cluster() -> bool:
    return bool(os.environ.get("KUBERNETES_SERVICE_HOST"))


def _is_artifact_registry(registry_url: str) -> bool:
    return "pkg.dev" in registry_url.lower() or "gcr.io" in registry_url.lower()


def build_via_kaniko_job(
    agent_id: str,
    registry_url: str,
    tag: str = "latest",
    control_plane_url: str = "http://ravp-control-plane.ravp.svc.cluster.local:8010",
    namespace: str = "ravp",
    control_plane_image: Optional[str] = None,
    timeout_seconds: int = 600,
) -> Tuple[bool, str, str]:
    """
    Create a Kaniko Job to build the agent image and push to registry_url.

    Args:
        agent_id: Agent identifier (must exist under agents/{agent_id}/)
        registry_url: Full image URL (e.g. us-central1-docker.pkg.dev/PROJECT/ravp-agents/agent-X:1.0.0)
        tag: Override tag (if not already in registry_url)
        control_plane_url: Value for CONTROL_PLANE_URL in the image
        namespace: K8s namespace for the Job (default: ravp)
        control_plane_image: Image for the init container (must have /app/agents, agent-sdk, config). Default: same as running pod.
        timeout_seconds: Max time to wait for Job completion

    Returns:
        (success, image_url_or_message, error_message)
    """
    try:
        from kubernetes import client, config
    except ImportError:
        return False, "", "kubernetes package not installed (pip install kubernetes)"
    if not _running_in_cluster():
        return False, "", "Not running in-cluster; use regular Docker build"
    if not _is_artifact_registry(registry_url):
        return False, "", "Kaniko build is only supported for Artifact Registry (pkg.dev) or GCR"

    # Ensure registry_url has a tag
    if ":" not in registry_url.split("/")[-1]:
        image_url = f"{registry_url}:{tag}"
    else:
        image_url = registry_url

    build_id = f"build-{uuid.uuid4().hex[:8]}"
    # Dockerfile comes only from control-plane code (build_service.generate_dockerfile_content)
    dockerfile_content = generate_dockerfile_content(agent_id, control_plane_url)

    try:
        config.load_incluster_config()
    except Exception as e:
        return False, "", f"Failed to load in-cluster config: {e}"

    # Use the same image as the control-plane for init (has agents/, agent-sdk/, config/)
    if not control_plane_image:
        control_plane_image = os.environ.get(
            "CONTROL_PLANE_IMAGE",
            "visanthoxdlbg/ravp:control-plane-1.0.0",
        )

    v1 = client.CoreV1Api()
    batch = client.BatchV1Api()

    # 1. ConfigMap with Dockerfile
    cm_name = f"agent-build-dockerfile-{build_id}"
    cm = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name=cm_name, namespace=namespace),
        data={"Dockerfile": dockerfile_content},
    )
    try:
        v1.create_namespaced_config_map(namespace, cm)
    except Exception as e:
        return False, "", f"Failed to create ConfigMap: {e}"

    # 2. PVC for build context (optional: use emptyDir in Job to avoid PVC)
    # We use emptyDir so we don't need to manage PVCs; the init and kaniko containers share it.
    # So no PVC creation.

    # 3. Job: init container copies context from control-plane image and, when available, config from PVC
    # (New agents created from the UI are stored in the config PVC; use it so the image has latest definitions.)
    job_name = f"agent-build-{build_id}"
    safe_agent_id = agent_id.replace("/", "").strip()
    init_script = (
        "set -e; "
        "mkdir -p /context/agents /context/agent-sdk /context/config /context/scripts /context/tools /context/data; "
        "cp /app/requirements.txt /context/; "
        f"cp -r /app/agents/{safe_agent_id} /context/agents/; "
        "cp -r /app/agent-sdk/* /context/agent-sdk/; "
        "cp -r /app/scripts/* /context/scripts/ 2>/dev/null || true; "
        "cp -r /app/tools/* /context/tools/ 2>/dev/null || true; "
        "cp -r /app/data/* /context/data/ 2>/dev/null || true; "
        # Prefer config from PVC (has UI-created agent definitions); fallback to image config
        "if [ -d /mnt/config ] && [ -n \"$(ls -A /mnt/config 2>/dev/null)\" ]; then "
        "cp -r /mnt/config/* /context/config/; "
        "else cp -r /app/config/* /context/config/; fi; "
        "cp /dockerfile/Dockerfile /context/Dockerfile; "
        "echo Done"
    )
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name=job_name, namespace=namespace),
        spec=client.V1JobSpec(
            ttl_seconds_after_finished=300,
            backoff_limit=1,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "ravp-agent-build", "build_id": build_id}),
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    init_containers=[
                        client.V1Container(
                            name="context",
                            image=control_plane_image,
                            command=["/bin/sh", "-c", init_script],
                            volume_mounts=[
                                client.V1VolumeMount(name="context", mount_path="/context"),
                                client.V1VolumeMount(name="dockerfile", mount_path="/dockerfile", read_only=True),
                                client.V1VolumeMount(name="config-pvc", mount_path="/mnt/config", read_only=True),
                            ],
                        ),
                    ],
                    containers=[
                        client.V1Container(
                            name="kaniko",
                            image="gcr.io/kaniko-project/executor:v1.19.2",
                            args=[
                                "--dockerfile=/context/Dockerfile",
                                "--context=dir:///context",
                                f"--destination={image_url}",
                                "--verbosity=info",
                            ],
                            volume_mounts=[
                                client.V1VolumeMount(name="context", mount_path="/context", read_only=True),
                            ],
                        ),
                    ],
                    volumes=[
                        client.V1Volume(name="context", empty_dir=client.V1EmptyDirVolumeSource()),
                        client.V1Volume(
                            name="dockerfile",
                            config_map=client.V1ConfigMapVolumeSource(name=cm_name),
                        ),
                        client.V1Volume(
                            name="config-pvc",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                claim_name="ravp-config-pvc", read_only=True
                            ),
                        ),
                    ],
                ),
            ),
        ),
    )

    try:
        batch.create_namespaced_job(namespace, job)
    except Exception as e:
        try:
            v1.delete_namespaced_config_map(cm_name, namespace)
        except Exception:
            pass
        return False, "", f"Failed to create Job: {e}"

    # Wait for job completion
    start = time.time()
    while time.time() - start < timeout_seconds:
        j = batch.read_namespaced_job_status(job_name, namespace)
        if j.status.succeeded and j.status.succeeded > 0:
            try:
                v1.delete_namespaced_config_map(cm_name, namespace)
            except Exception:
                pass
            return True, image_url, ""
        if j.status.failed and j.status.failed > 0:
            # Get pod logs for failure reason
            pods = v1.list_namespaced_pod(
                namespace,
                label_selector=f"job-name={job_name}",
            )
            err_msg = "Build job failed"
            for p in pods.items:
                if p.status.phase == "Failed" or (p.status.container_statuses or []):
                    for cs in p.status.container_statuses or []:
                        if cs.state and cs.state.terminated and cs.state.terminated.reason:
                            err_msg = cs.state.terminated.message or cs.state.terminated.reason
                    break
            try:
                v1.delete_namespaced_config_map(cm_name, namespace)
            except Exception:
                pass
            return False, "", err_msg
        time.sleep(5)

    try:
        v1.delete_namespaced_config_map(cm_name, namespace)
    except Exception:
        pass
    return False, "", f"Build timed out after {timeout_seconds}s. Check job: kubectl get job -n {namespace} {job_name}"
