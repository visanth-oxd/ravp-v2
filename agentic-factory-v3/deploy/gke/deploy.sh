#!/usr/bin/env bash
# Build RAVP images and optionally push to a registry, then deploy to GKE.
# Run from the repository root: ./deploy/gke/deploy.sh

set -e

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

# Image tag (default: latest). Set REGISTRY to push (e.g. us-docker.pkg.dev/MY_PROJECT/ravp)
TAG="${TAG:-latest}"
REGISTRY="${REGISTRY:-}"

echo "=== Building RAVP images (tag=$TAG) ==="
docker build -f deploy/gke/Dockerfile.control-plane -t ravp-control-plane:"$TAG" .
docker build -f deploy/gke/Dockerfile.platform-ui    -t ravp-platform-ui:"$TAG" .

if [ -n "$REGISTRY" ]; then
  echo "=== Pushing to $REGISTRY ==="
  docker tag ravp-control-plane:"$TAG" "$REGISTRY/ravp-control-plane:$TAG"
  docker tag ravp-platform-ui:"$TAG"    "$REGISTRY/ravp-platform-ui:$TAG"
  docker push "$REGISTRY/ravp-control-plane:$TAG"
  docker push "$REGISTRY/ravp-platform-ui:$TAG"
  export CONTROL_PLANE_IMAGE="$REGISTRY/ravp-control-plane:$TAG"
  export PLATFORM_UI_IMAGE="$REGISTRY/ravp-platform-ui:$TAG"
fi

echo "=== Deploying to Kubernetes (namespace ravp) ==="
kubectl apply -f deploy/gke/kubernetes/namespace.yaml
kubectl apply -f deploy/gke/kubernetes/control-plane-deployment.yaml
kubectl apply -f deploy/gke/kubernetes/control-plane-service.yaml
kubectl apply -f deploy/gke/kubernetes/platform-ui-deployment.yaml
kubectl apply -f deploy/gke/kubernetes/platform-ui-service.yaml
# RBAC for in-cluster agent image build (Kaniko)
kubectl apply -f deploy/gke/kubernetes/control-plane-rbac-builds.yaml

if [ -n "$REGISTRY" ]; then
  echo "=== Setting deployment images to registry ==="
  kubectl set image deployment/ravp-control-plane -n ravp control-plane="$CONTROL_PLANE_IMAGE"
  kubectl set image deployment/ravp-platform-ui -n ravp platform-ui="$PLATFORM_UI_IMAGE"
fi

echo "=== Ingress (ravp-ai.co.uk) ==="
# Ingress uses static IP 'ravp-ip'. Create it first if needed:
#   gcloud compute addresses create ravp-ip --global
kubectl apply -f deploy/gke/kubernetes/ingress.yaml

if [ -n "${ENABLE_HTTPS:-}" ]; then
  echo "=== Managed certificate (HTTPS) ==="
  kubectl apply -f deploy/gke/kubernetes/managed-certificate.yaml
  echo "Add to ingress.yaml metadata.annotations: networking.gke.io/managed-certificates: \"ravp-cert\" then re-apply ingress."
fi

echo ""
echo "Done."
echo "  Local access:  kubectl port-forward -n ravp svc/ravp-platform-ui 8501:8501  → http://localhost:8501"
echo "  Custom domain: Ensure static IP exists (gcloud compute addresses create ravp-ip --global), then point ravp-ai.co.uk A record to that IP."
echo "  Ingress status: kubectl get ingress -n ravp"
