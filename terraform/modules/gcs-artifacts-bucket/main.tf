locals {
  name_prefix = "app-${var.environment}"
}

resource "google_storage_bucket" "artifacts" {
  name                        = "${var.project_id}-${local.name_prefix}-artifacts"
  location                    = var.region
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}
