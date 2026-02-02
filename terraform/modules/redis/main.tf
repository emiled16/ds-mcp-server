locals {
  name_prefix = "app-${var.environment}"
}

resource "google_redis_instance" "redis" {
  name           = "${local.name_prefix}-redis"
  tier           = "BASIC"
  memory_size_gb = var.redis_memory_gb
  region         = var.region

  authorized_network = var.network_id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"
}
