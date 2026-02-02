#!/usr/bin/env bash
# Verify billable GCP resources from Terraform are destroyed.
# Run after `make tf-destroy` to confirm no costs remain.
# Usage: ./scripts/verify-costs.sh [project_id] [region]
#   Or set PROJECT_ID and REGION env vars, or run via `make verify-costs` (reads from terraform).

set -e

# Resource names (default env = dev)
NAME_PREFIX="${NAME_PREFIX:-app-dev}"

# Resolve PROJECT_ID and REGION
resolve_config() {
  if [[ -n "$1" && -n "$2" ]]; then
    PROJECT_ID="$1"
    REGION="$2"
    ARTIFACT_REGION="${REGION}"
    return
  fi
  if [[ -n "$PROJECT_ID" && -n "$REGION" ]]; then
    ARTIFACT_REGION="${ARTIFACT_REGION:-$REGION}"
    return
  fi
  TF_DIR="$(cd "$(dirname "$0")/.." && pwd)/terraform/envs/dev"
  PROJECT_ID=""
  REGION=""
  # Try terraform output (requires state)
  if [[ -d "$TF_DIR" ]]; then
    (cd "$TF_DIR" && terraform output -raw project_id &>/dev/null) && {
      PROJECT_ID="$(cd "$TF_DIR" && terraform output -raw project_id)"
      REGION="$(cd "$TF_DIR" && terraform output -raw gke_location 2>/dev/null)" || true
    }
  fi
  # Fallback: parse terraform.tfvars
  if [[ -z "$PROJECT_ID" && -f "$TF_DIR/terraform.tfvars" ]]; then
    PROJECT_ID="$(grep -E '^\s*project_id\s*=' "$TF_DIR/terraform.tfvars" | sed -E 's/.*"([^"]+)".*/\1/' | head -1)"
    REGION="$(grep -E '^\s*region\s*=' "$TF_DIR/terraform.tfvars" | sed -E 's/.*"([^"]+)".*/\1/' | head -1)"
  fi
  if [[ -z "$PROJECT_ID" ]]; then
    echo "Error: PROJECT_ID required. Set env PROJECT_ID and REGION, or: $0 <project_id> <region>"
    exit 1
  fi
  REGION="${REGION:-us-central1}"
  ARTIFACT_REGION="${ARTIFACT_REGION:-$REGION}"
}

# Check if a resource exists; return 0 if found, 1 if not
check_gke() {
  gcloud container clusters list --project="$PROJECT_ID" --format="value(name)" 2>/dev/null | grep -q "^${NAME_PREFIX}-gke$"
}

check_cloudsql() {
  gcloud sql instances list --project="$PROJECT_ID" --format="value(name)" 2>/dev/null | grep -q "^${NAME_PREFIX}-pg$"
}

check_redis() {
  gcloud redis instances list --project="$PROJECT_ID" --region="$REGION" --format="value(name)" 2>/dev/null | grep -q "^${NAME_PREFIX}-redis$"
}

check_artifact_registry() {
  gcloud artifacts repositories list --project="$PROJECT_ID" --location="${ARTIFACT_REGION}" --format="value(name)" 2>/dev/null | grep -q "^${NAME_PREFIX}-repo$"
}

check_gcs_bucket() {
  gcloud storage buckets list --project="$PROJECT_ID" --format="value(name)" 2>/dev/null | grep -q "^${PROJECT_ID}-${NAME_PREFIX}-artifacts$"
}

# Print report row
report_row() {
  local status="$1"
  local service="$2"
  local resource="$3"
  if [[ "$status" == "DESTROYED" ]]; then
    printf "  %-20s %-30s \033[32m%s\033[0m\n" "$service" "$resource" "✓ DESTROYED"
  else
    printf "  %-20s %-30s \033[31m%s\033[0m\n" "$service" "$resource" "✗ FOUND (costing)"
  fi
}

# Main
resolve_config "$@"

echo "=============================================="
echo "  GCP Cost Verification Report"
echo "=============================================="
echo "  Project: $PROJECT_ID"
echo "  Region:  $REGION"
echo "  Prefix:  $NAME_PREFIX"
echo "----------------------------------------------"

FOUND=0

if check_gke; then
  report_row "FOUND" "GKE" "${NAME_PREFIX}-gke"
  FOUND=$((FOUND + 1))
else
  report_row "DESTROYED" "GKE" "${NAME_PREFIX}-gke"
fi

if check_cloudsql; then
  report_row "FOUND" "Cloud SQL" "${NAME_PREFIX}-pg"
  FOUND=$((FOUND + 1))
else
  report_row "DESTROYED" "Cloud SQL" "${NAME_PREFIX}-pg"
fi

if check_redis; then
  report_row "FOUND" "Memorystore Redis" "${NAME_PREFIX}-redis"
  FOUND=$((FOUND + 1))
else
  report_row "DESTROYED" "Memorystore Redis" "${NAME_PREFIX}-redis"
fi

if check_artifact_registry; then
  report_row "FOUND" "Artifact Registry" "${NAME_PREFIX}-repo"
  FOUND=$((FOUND + 1))
else
  report_row "DESTROYED" "Artifact Registry" "${NAME_PREFIX}-repo"
fi

if check_gcs_bucket; then
  report_row "FOUND" "Cloud Storage" "${PROJECT_ID}-${NAME_PREFIX}-artifacts"
  FOUND=$((FOUND + 1))
else
  report_row "DESTROYED" "Cloud Storage" "${PROJECT_ID}-${NAME_PREFIX}-artifacts"
fi

echo "----------------------------------------------"
if [[ $FOUND -eq 0 ]]; then
  echo "  Result: All billable resources destroyed. ✓"
  exit 0
else
  echo "  Result: $FOUND resource(s) still exist. Run \`make tf-destroy\` or delete manually."
  exit 1
fi
