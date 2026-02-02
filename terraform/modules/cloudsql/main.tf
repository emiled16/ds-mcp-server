locals {
  name_prefix = "app-${var.environment}"
}

resource "google_sql_database_instance" "postgres" {
  name             = "${local.name_prefix}-pg"
  database_version = var.database_version
  region           = var.region

  settings {
    tier = var.cloudsql_tier

    disk_type = "PD_SSD"
    disk_size = var.cloudsql_disk_gb

    backup_configuration {
      enabled = true
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.network_id
    }
  }
}

resource "google_sql_database" "app_db" {
  name     = var.database_name
  instance = google_sql_database_instance.postgres.name
}

# Password should not be created by Terraform for real production because it lands in state.
# For learning, you should create it in Secret Manager and sync into Kubernetes via ESO.
resource "google_sql_user" "app_user" {
  name     = var.user_name
  instance = google_sql_database_instance.postgres.name
  password = var.user_password
}
