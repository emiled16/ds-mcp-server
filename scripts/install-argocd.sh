#!/usr/bin/env bash
# Install Argo CD into the current Kubernetes cluster (GKE).
# Prerequisites: run `make kube-connect` first to connect kubectl to the cluster.
#
# Usage: ./scripts/install-argocd.sh [repo_url]
#   repo_url: optional - if provided, applies argocd/application.yaml with REPO_URL replaced
#   Or set REPO_URL env var. If unset, only installs Argo CD (you apply the Application manually).
#
# Example: ./scripts/install-argocd.sh https://github.com/emiled16/ds-mcp-server

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_URL="${1:-${REPO_URL}}"

echo "=== Argo CD installation ==="

# Check kubectl connection
if ! kubectl cluster-info &>/dev/null; then
  echo "Error: kubectl is not connected to a cluster. Run 'make kube-connect' first."
  exit 1
fi

echo "Cluster: $(kubectl config current-context)"

# Create namespace
echo ""
echo "Creating argocd namespace..."
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -

# Add Helm repo and install
echo ""
echo "Adding Argo Helm repo..."
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

echo ""
echo "Installing Argo CD..."
helm upgrade --install argocd argo/argo-cd -n argocd --set installCRDs=true

# Wait for Argo CD to be ready
echo ""
echo "Waiting for Argo CD server to be ready (timeout 300s)..."
kubectl wait --for=condition=Available deployment/argocd-server -n argocd --timeout=300s

echo ""
echo "Argo CD is installed and ready."

# Get initial admin password
echo ""
echo "Initial admin password (save this):"
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>/dev/null | base64 -d
echo ""
echo ""

# Apply Application manifest if REPO_URL provided
if [[ -n "$REPO_URL" ]]; then
  echo "Applying Argo CD Application (repo: $REPO_URL)..."
  sed "s|REPO_URL|$REPO_URL|g" "$REPO_ROOT/argocd/application.yaml" | kubectl apply -f -
  echo "Application applied. Argo CD will sync charts/my-app from the repo."
else
  echo "To register the app with Argo CD:"
  echo "  1. Edit argocd/application.yaml - replace REPO_URL with your repo URL"
  echo "  2. kubectl apply -f argocd/application.yaml"
  echo ""
  echo "Or run: ./scripts/install-argocd.sh https://github.com/your-org/ds-mcp-server"
fi

echo ""
echo "Optional: Port-forward to access Argo CD UI:"
echo "  kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo "  Open https://localhost:8080 (accept self-signed cert)"
