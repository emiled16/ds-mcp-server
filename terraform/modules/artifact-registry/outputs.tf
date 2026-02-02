output "repo_url" {
  value = "${google_artifact_registry_repository.repo.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}"
}

output "repo_id" { value = google_artifact_registry_repository.repo.repository_id }
