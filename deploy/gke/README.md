# Run RAVP on GKE

This folder packages the **Regulated Agent Vending Platform (RAVP)** for Google Kubernetes Engine: control-plane API and Streamlit platform UI.

## What’s included

| Item | Description |
|------|-------------|
| `Dockerfile.control-plane` | Control-plane API (FastAPI, port 8010) |
| `Dockerfile.platform-ui` | Streamlit UI (port 8501), uses `API_URL` to talk to control-plane |
| `kubernetes/*.yaml` | Namespace `ravp`, Deployments, Services, optional Ingress |
| `deploy.sh` | Build images, optionally push, then `kubectl apply` |

## Prerequisites

- **Docker** – to build images
- **kubectl** – configured for your GKE cluster
- **gcloud** – for GKE and (if you push images) Artifact Registry auth

## 1. Build and run locally (no GKE)

From the **repository root**:

```bash
# Control-plane
docker build -f deploy/gke/Dockerfile.control-plane -t ravp-control-plane .
docker run -p 8010:8010 ravp-control-plane

# UI (in another terminal); point to control-plane
docker run -p 8501:8501 -e API_URL=http://host.docker.internal:8010 ravp-platform-ui
```

Then open http://localhost:8501 (on Mac/Windows `host.docker.internal` reaches the host; on Linux use the host IP or run both in the same network).

## 2. Deploy to GKE (using default images)

If your cluster can use local/default images (e.g. kind, or GKE with the images loaded):

```bash
# From repo root
./deploy/gke/deploy.sh
```

Then:

```bash
kubectl port-forward -n ravp svc/ravp-platform-ui 8501:8501
# Open http://localhost:8501
```

## 3. Build, push to a registry, then deploy

For a real GKE cluster you usually push images to **Google Artifact Registry** (or GCR), then point the deployments at those images.

### 3.1 Create a Docker repo (Artifact Registry)

```bash
# Set your GCP project and region
export PROJECT_ID=your-gcp-project
export REGION=us-central1

gcloud artifacts repositories create ravp --repository-format=docker --location="$REGION"
```

### 3.2 Configure Docker to use Artifact Registry

```bash
gcloud auth configure-docker "$REGION-docker.pkg.dev"
```

### 3.3 Build, tag, and push

From repo root:

```bash
export REGISTRY="$REGION-docker.pkg.dev/$PROJECT_ID/ravp"
export TAG=latest

./deploy/gke/deploy.sh
```

`deploy.sh` builds both images, tags them as `$REGISTRY/ravp-control-plane:$TAG` and `$REGISTRY/ravp-platform-ui:$TAG`, pushes them, then runs `kubectl apply`. The manifests use `ravp-control-plane:latest` and `ravp-platform-ui:latest` by default. For a pushed registry you must **set the image** in the deployments to `$REGISTRY/ravp-control-plane:$TAG` and `$REGISTRY/ravp-platform-ui:$TAG` (or patch after apply):

```bash
kubectl set image deployment/ravp-control-plane -n ravp control-plane=$REGISTRY/ravp-control-plane:$TAG
kubectl set image deployment/ravp-platform-ui -n ravp platform-ui=$REGISTRY/ravp-platform-ui:$TAG
```

### 3.4 GKE pull from Artifact Registry

If the cluster is in the same project, GKE can pull from Artifact Registry without extra secrets. Otherwise attach a pull secret or use a GKE service account with `roles/artifactregistry.reader`.

## 4. Expose the UI (Ingress or LoadBalancer)

- **Quick test:** keep using `kubectl port-forward` as above.
- **LoadBalancer:** change `ravp-platform-ui` Service to `type: LoadBalancer` and use the external IP.
- **Ingress:** use `deploy/gke/kubernetes/ingress.yaml` (see section 5 for custom domain).

## 5. Map your domain (ravp-ai.co.uk) to GKE

Once RAVP is deployed on GKE, you can serve it at **ravp-ai.co.uk** (or **www.ravp-ai.co.uk**) as follows.

### 5.1 Reserve a static IP in GCP

GKE Ingress will get an external IP; if you don’t reserve it, the IP can change and your DNS would break. Reserve a **global** static IP:

```bash
gcloud compute addresses create ravp-ip --global
```

Get the address (you’ll use it for DNS):

```bash
gcloud compute addresses describe ravp-ip --global --format="get(address)"
```

### 5.2 Deploy the Ingress with your domain

The file `kubernetes/ingress.yaml` is already set up for **ravp-ai.co.uk** and uses the static IP name `ravp-ip`. If you used a different name in step 5.1, change the annotation in `ingress.yaml`:

```yaml
annotations:
  kubernetes.io/ingress.global-static-ip-name: "ravp-ip"   # your reserved IP name
```

Apply the Ingress:

```bash
kubectl apply -f deploy/gke/kubernetes/ingress.yaml
```

Wait for the Ingress to get an external IP (it will use your reserved IP). Check:

```bash
kubectl get ingress -n ravp
```

The **ADDRESS** column should show the same IP as `gcloud compute addresses describe ravp-ip --global`.

### 5.3 Point your domain to that IP (DNS)

At the registrar or DNS provider where **ravp-ai.co.uk** is managed:

| Type | Name / Host | Value / Target        | TTL  |
|------|-------------|------------------------|------|
| **A**  | `@`         | `<static-IP-from-5.1>` | 300  |
| **A**  | `www`       | `<static-IP-from-5.1>` | 300  |

- **@** = root domain **ravp-ai.co.uk**
- **www** = **www.ravp-ai.co.uk**

Use the **exact** IP from `gcloud compute addresses describe ravp-ip --global --format="get(address)"`. DNS can take a few minutes up to 48 hours to propagate.

### 5.4 (Optional) HTTPS with a Google-managed certificate

The Ingress is already set up for **ravp-ai.co.uk** and **www.ravp-ai.co.uk**. To enable HTTPS:

1. Apply the managed certificate:
   ```bash
   kubectl apply -f deploy/gke/kubernetes/managed-certificate.yaml
   ```
2. Edit `deploy/gke/kubernetes/ingress.yaml` and add this annotation under `metadata.annotations`:
   ```yaml
   networking.gke.io/managed-certificates: "ravp-cert"
   ```
3. Re-apply the Ingress:
   ```bash
   kubectl apply -f deploy/gke/kubernetes/ingress.yaml
   ```
4. Wait 15–60 minutes for the certificate to be provisioned. Check status:
   ```bash
   kubectl describe managedcertificate ravp-cert -n ravp
   ```

After DNS propagates, open **http://ravp-ai.co.uk** (and **https://ravp-ai.co.uk** once the cert is active).

## 6. Summary

| Step | Command (from repo root) |
|------|--------------------------|
| Build only | `docker build -f deploy/gke/Dockerfile.control-plane -t ravp-control-plane .` and same for `Dockerfile.platform-ui` |
| Deploy (no push) | `./deploy/gke/deploy.sh` |
| Build + push + deploy | `REGISTRY=us-docker.pkg.dev/PROJECT/ravp ./deploy/gke/deploy.sh` then set image in deployments |
| Access UI (local) | `kubectl port-forward -n ravp svc/ravp-platform-ui 8501:8501` → http://localhost:8501 |
| Custom domain | Reserve static IP → apply `kubernetes/ingress.yaml` → add A record for **ravp-ai.co.uk** to that IP (see section 5) |

The platform UI talks to the control-plane via `API_URL`; in-cluster this is set to `http://ravp-control-plane.ravp.svc.cluster.local:8010`.
