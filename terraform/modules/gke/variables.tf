variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }

variable "network_id" { type = string }
variable "subnet_id" { type = string }

variable "gke_min_nodes" { type = number }
variable "gke_max_nodes" { type = number }
variable "gke_machine_type" { type = string }
