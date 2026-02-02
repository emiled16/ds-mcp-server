
terraform {
  backend "gcs" {
    bucket = "data-science-mcp-tfstate"
    prefix = "dev"
  }
}
