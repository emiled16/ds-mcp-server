variable "region" { type = string }
variable "environment" { type = string }
variable "network_id" { type = string }

variable "cloudsql_tier" { type = string }
variable "cloudsql_disk_gb" { type = number }

variable "database_version" {
  type    = string
  default = "POSTGRES_15"
}

variable "database_name" {
  type    = string
  default = "mlflow"
}

variable "user_name" {
  type    = string
  default = "appuser"
}

variable "user_password" {
  type    = string
  default = "CHANGE_ME_IN_SECRET_MANAGER"
}
