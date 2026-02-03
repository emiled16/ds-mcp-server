# ds-mcp-server

Single repository for the MCP data-science platform: **infrastructure** (Terraform + Helm), **charts**, and **application** code.

## Structure

```
ds-mcp-server/
├── app/          # Python application (MCP server, Celery, MLflow, Flower)
│   ├── src/
│   ├── docker/
│   ├── tests/
│   └── pyproject.toml
├── terraform/    # Terraform (GKE, Cloud SQL, Redis, etc.)
│   ├── envs/dev/
│   └── modules/
├── charts/       # Helm chart (my-app)
├── argocd/       # Argo CD bootstrap (GitOps)
├── docs/         # Deployment and assessment docs
└── .github/      # CI/CD workflows (release-please, Docker, Terraform)
```

## Quick start

- **App (local):** See `app/README.md` and `app/pyproject.toml`. Run from `app/` with Poetry.
- **Infra:** See `docs/INSTRUCTIONS.md` and `docs/DEPLOYMENT.md`. Terraform lives under `terraform/envs/dev/`; Helm chart under `charts/my-app/`.

## Workflows (root `.github/workflows/`)

- **release-please:** On push to `main`, creates/updates release PR from conventional commits; on merge, bumps version and creates a GitHub release.
- **ci:** On push/PR to `main` — app lint (ruff) and unit tests in `app/`.
- **terraform:** On PR/push when `terraform/**` changes — plan on PR, apply on `main` (use environment `terraform-apply` for apply).
- **docker:** On push to `main` when `app/**` changes — build MCP/Celery/Flower and MLflow images from `app/`, push to Artifact Registry (tag = git SHA + `latest`).
- **Deploy:** Argo CD syncs the Helm chart from this repo (GitOps); see `docs/DEPLOYMENT.md`.

**Required GitHub secrets:** `GCP_SA_KEY`, `ARTIFACT_REGISTRY_REPO` (e.g. `REGION-docker.pkg.dev/PROJECT/REPO`).
