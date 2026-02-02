variable "project_id" { type = string }

variable "gsa_account_id" {
  type    = string
  default = "external-secrets-gsa"
}

variable "k8s_namespace" {
  type    = string
  default = "external-secrets"
}

variable "k8s_service_account" {
  type    = string
  default = "external-secrets-sa"
}
