provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "EcoCiente"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}