# Terraform Makefile
# Use for local apply/destroy when learning. Destroy infra when not working to avoid costs.

TF_DIR := terraform/envs/dev
TF_VAR_FILE := terraform.tfvars

# Use -var-file only if terraform.tfvars exists
TF_PLAN_ARGS := -input=false
ifneq ($(wildcard $(TF_DIR)/$(TF_VAR_FILE)),)
  TF_PLAN_ARGS += -var-file=$(TF_VAR_FILE)
endif

.PHONY: tf-init tf-plan tf-apply tf-destroy tf-fmt tf-validate kube-connect kube-disconnect verify-costs install-argocd setup-github-oidc tf-help

tf-init:
	cd $(TF_DIR) && terraform init -input=false

tf-fmt:
	cd $(TF_DIR) && terraform fmt -recursive

tf-validate: tf-init
	cd $(TF_DIR) && terraform validate

tf-plan: tf-validate
	cd $(TF_DIR) && terraform plan $(TF_PLAN_ARGS)

tf-apply: tf-validate
	@echo "Applying Terraform changes..."
	cd $(TF_DIR) && terraform apply $(TF_PLAN_ARGS)

tf-destroy: tf-validate
	@echo "WARNING: This will destroy all infrastructure. Terraform will prompt for confirmation."
	cd $(TF_DIR) && terraform destroy $(TF_PLAN_ARGS)

# Kubectl: connect to GKE cluster (requires tf-apply first) and disconnect
kube-connect: tf-init
	@echo "Fetching cluster credentials..."
	@cd $(TF_DIR) && \
	  PROJECT_ID=$$(terraform output -raw project_id) && \
	  CLUSTER_NAME=$$(terraform output -raw gke_cluster_name) && \
	  LOCATION=$$(terraform output -raw gke_location) && \
	  gcloud container clusters get-credentials "$$CLUSTER_NAME" \
	    --region "$$LOCATION" --project "$$PROJECT_ID"
	@echo "Connected. Verifying..."
	@kubectl get nodes

kube-disconnect: tf-init
	@cd $(TF_DIR) && \
	  PROJECT_ID=$$(terraform output -raw project_id) && \
	  CLUSTER_NAME=$$(terraform output -raw gke_cluster_name) && \
	  LOCATION=$$(terraform output -raw gke_location) && \
	  CONTEXT="gke_$${PROJECT_ID}_$${LOCATION}_$${CLUSTER_NAME}" && \
	  kubectl config delete-context "$$CONTEXT" 2>/dev/null || true
	@echo "Disconnected from GKE cluster."

# Verify billable GCP resources are destroyed (run after tf-destroy)
verify-costs:
	@./scripts/verify-costs.sh

# Install Argo CD into the cluster (requires kube-connect first)
# Usage: make install-argocd REPO_URL=https://github.com/your-org/ds-mcp-server
#   Or: make install-argocd  (installs Argo CD only, apply Application manually)
install-argocd:
	@./scripts/install-argocd.sh $(REPO_URL)

# Set up GitHub Actions OIDC (Workload Identity Federation) - run once
# Usage: make setup-github-oidc GITHUB_REPO=owner/repo
setup-github-oidc:
	@./scripts/setup-github-oidc.sh $(GITHUB_REPO)

# Convenience aliases
tf: tf-plan
apply: tf-apply
destroy: tf-destroy

tf-help:
	@echo "Terraform targets (run from project root):"
	@echo "  make tf-init       - Initialize Terraform"
	@echo "  make tf-plan       - Plan changes (dry-run)"
	@echo "  make tf-apply      - Apply infrastructure"
	@echo "  make tf-destroy    - Destroy infrastructure (saves costs when not working)"
	@echo "  make tf-fmt        - Format Terraform files"
	@echo "  make tf-validate   - Validate configuration"
	@echo ""
	@echo "Kubectl targets (connect to GKE after tf-apply):"
	@echo "  make kube-connect    - Fetch credentials and connect kubectl to the GKE cluster"
	@echo "  make kube-disconnect - Remove the GKE context from kubeconfig"
	@echo ""
	@echo "Verification (after tf-destroy):"
	@echo "  make verify-costs    - Check that all billable GCP resources are destroyed"
	@echo ""
	@echo "Argo CD (after kube-connect):"
	@echo "  make install-argocd  - Install Argo CD. Use REPO_URL=https://... to also apply Application"
	@echo ""
	@echo "GitHub Actions OIDC (one-time setup):"
	@echo "  make setup-github-oidc GITHUB_REPO=owner/repo  - Set up Workload Identity for GitHub Actions"
	@echo ""
	@echo "Ensure terraform/envs/dev/terraform.tfvars exists with project_id, region, zone."
