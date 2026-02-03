
module "network" {
  source = "../../modules/network"

  region      = var.region
  environment = var.environment

  network_name = var.network_name
  subnet_cidr  = var.subnet_cidr
}

module "artifact_registry" {
  source = "../../modules/artifact-registry"

  project_id  = var.project_id
  environment = var.environment
  location    = var.artifact_registry_location
}

module "gcs_artifacts_bucket" {
  source = "../../modules/gcs-artifacts-bucket"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment
}

module "gke" {
  source = "../../modules/gke"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment

  network_id = module.network.network_id
  subnet_id  = module.network.subnet_id

  gke_min_nodes    = var.gke_min_nodes
  gke_max_nodes    = var.gke_max_nodes
  gke_machine_type = var.gke_machine_type
}

module "external_secrets" {
  source = "../../modules/external-secrets"

  project_id = var.project_id
}

module "cloudsql" {
  source = "../../modules/cloudsql"

  region      = var.region
  environment = var.environment
  network_id  = module.network.network_id

  cloudsql_tier    = var.cloudsql_tier
  cloudsql_disk_gb = var.cloudsql_disk_gb

  depends_on = [module.network]
}

module "redis" {
  source = "../../modules/redis"

  region      = var.region
  environment = var.environment
  network_id  = module.network.network_id

  redis_memory_gb = var.redis_memory_gb

  depends_on = [module.network]
}

output "project_id" { value = var.project_id }
output "gke_cluster_name" { value = module.gke.cluster_name }
output "gke_location" { value = module.gke.cluster_location }
output "artifact_registry_repo" { value = module.artifact_registry.repo_url }
output "gcs_artifacts_bucket" { value = module.gcs_artifacts_bucket.bucket_name }
output "cloudsql_private_ip" { value = module.cloudsql.private_ip }
output "redis_host" { value = module.redis.host }
output "external_secrets_gsa_email" { value = module.external_secrets.gsa_email }

# GCS bucket access for app pods (MCP, Celery, MLflow) via GKE node SA
resource "google_storage_bucket_iam_member" "gke_nodes_artifacts_writer" {
  bucket = module.gcs_artifacts_bucket.bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${module.gke.node_service_account_email}"
}
