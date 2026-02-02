
variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "zone" {
  type = string
}

variable "network_name" {
  type    = string
  default = "app-vpc"
}

variable "subnet_cidr" {
  type    = string
  default = "10.10.0.0/16"
}

variable "artifact_registry_location" {
  type    = string
  default = "us-central1"
}

variable "environment" {
  type    = string
  default = "dev"
}

# Learning-cost defaults
variable "gke_min_nodes" {
  type    = number
  default = 1
}

variable "gke_max_nodes" {
  type    = number
  default = 1
}

variable "gke_machine_type" {
  type    = string
  default = "e2-standard-2"
}

variable "cloudsql_tier" {
  type    = string
  default = "db-f1-micro"
}

variable "cloudsql_disk_gb" {
  type    = number
  default = 10
}

variable "redis_memory_gb" {
  type    = number
  default = 1
}
