locals {
  name_prefix = "app-${var.environment}"
}

resource "google_artifact_registry_repository" "repo" {
  location      = var.location
  repository_id = "${local.name_prefix}-repo"
  description   = "Docker images for ${local.name_prefix}"
  format        = "DOCKER"
}
