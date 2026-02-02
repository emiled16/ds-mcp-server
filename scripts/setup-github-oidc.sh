#!/usr/bin/env bash
# Set up Workload Identity Federation for GitHub Actions (OIDC).
# Run once to enable GitHub Actions to authenticate to GCP without JSON keys.
#
# Usage: ./scripts/setup-github-oidc.sh <github_repo>
#   github_repo: GitHub repository in format owner/repo (e.g. emiled16/ds-mcp-server)
#
# Prerequisites:
#   - gcloud CLI authenticated with sufficient permissions
#   - PROJECT_ID set in environment or terraform.tfvars
#
# Example:
#   ./scripts/setup-github-oidc.sh emiled16/ds-mcp-server

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TF_DIR="$REPO_ROOT/terraform/envs/dev"

# Configuration
POOL_ID="github-pool"
PROVIDER_ID="github-provider"
SA_ID="github-ci-sa"

# Get GitHub repo from argument
GITHUB_REPO="${1:-}"
if [[ -z "$GITHUB_REPO" ]]; then
  echo "Usage: $0 <github_repo>"
  echo "  github_repo: GitHub repository in format owner/repo (e.g. emiled16/ds-mcp-server)"
  exit 1
fi

# Get PROJECT_ID from environment or terraform.tfvars
if [[ -z "$PROJECT_ID" ]]; then
  if [[ -f "$TF_DIR/terraform.tfvars" ]]; then
    PROJECT_ID="$(grep -E '^\s*project_id\s*=' "$TF_DIR/terraform.tfvars" | sed -E 's/.*"([^"]+)".*/\1/' | head -1)"
  fi
fi

if [[ -z "$PROJECT_ID" ]]; then
  echo "Error: PROJECT_ID not set. Set it in environment or terraform/envs/dev/terraform.tfvars"
  exit 1
fi

# Get project number
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")

echo "=============================================="
echo "  GitHub OIDC Setup (Workload Identity)"
echo "=============================================="
echo "  Project ID:     $PROJECT_ID"
echo "  Project Number: $PROJECT_NUMBER"
echo "  GitHub Repo:    $GITHUB_REPO"
echo "----------------------------------------------"

# Enable required API
echo ""
echo "Enabling IAM Credentials API..."
gcloud services enable iamcredentials.googleapis.com --project="$PROJECT_ID"

# Create service account
echo ""
echo "Creating service account: $SA_ID..."
if gcloud iam service-accounts describe "${SA_ID}@${PROJECT_ID}.iam.gserviceaccount.com" --project="$PROJECT_ID" &>/dev/null; then
  echo "  Service account already exists, skipping creation."
else
  gcloud iam service-accounts create "$SA_ID" \
    --display-name="GitHub CI Service Account" \
    --project="$PROJECT_ID"
fi

SA_EMAIL="${SA_ID}@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant Artifact Registry writer
echo ""
echo "Granting Artifact Registry writer role..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.writer" \
  --condition=None \
  --quiet

# Create Workload Identity Pool
echo ""
echo "Creating Workload Identity Pool: $POOL_ID..."
if gcloud iam workload-identity-pools describe "$POOL_ID" --location="global" --project="$PROJECT_ID" &>/dev/null; then
  echo "  Pool already exists, skipping creation."
else
  gcloud iam workload-identity-pools create "$POOL_ID" \
    --project="$PROJECT_ID" \
    --location="global" \
    --display-name="GitHub Actions Pool" \
    --description="Workload Identity Pool for GitHub Actions"
fi

# Create OIDC Provider
echo ""
echo "Creating OIDC Provider: $PROVIDER_ID..."
if gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" \
    --workload-identity-pool="$POOL_ID" \
    --location="global" \
    --project="$PROJECT_ID" &>/dev/null; then
  echo "  Provider already exists, skipping creation."
else
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
    --project="$PROJECT_ID" \
    --location="global" \
    --workload-identity-pool="$POOL_ID" \
    --display-name="GitHub Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
    --attribute-condition="assertion.repository=='${GITHUB_REPO}'" \
    --issuer-uri="https://token.actions.githubusercontent.com"
fi

# Allow GitHub repo to impersonate the service account
echo ""
echo "Binding GitHub repo to service account..."
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${GITHUB_REPO}" \
  --condition=None \
  --quiet

# Output values for GitHub workflow
PROVIDER_RESOURCE="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"

echo ""
echo "=============================================="
echo "  OIDC Setup Complete!"
echo "=============================================="
echo ""
echo "Use these values in your GitHub workflow:"
echo ""
echo "  WORKLOAD_IDENTITY_PROVIDER:"
echo "    $PROVIDER_RESOURCE"
echo ""
echo "  SERVICE_ACCOUNT:"
echo "    $SA_EMAIL"
echo ""
echo "Example workflow snippet:"
echo ""
cat <<'EOF'
    permissions:
      contents: read
      id-token: write   # Required for OIDC

    steps:
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: "WORKLOAD_IDENTITY_PROVIDER"
          service_account: "SERVICE_ACCOUNT"
EOF
echo ""
echo "Replace WORKLOAD_IDENTITY_PROVIDER and SERVICE_ACCOUNT with the values above."
