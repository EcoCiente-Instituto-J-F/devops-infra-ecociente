variable "aws_region" {
  description = "Regiao AWS utilizada pela infraestrutura do EcoCiente."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nome utilizado para identificar os recursos do EcoCiente."
  type        = string
  default     = "ecociente"
}

variable "environment" {
  description = "Ambiente da infraestrutura."
  type        = string
  default     = "aws-lab"
}

variable "vpc_cidr" {
  description = "Bloco CIDR utilizado pela VPC do EcoCiente."
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidr" {
  description = "Bloco CIDR utilizado pela subnet publica."
  type        = string
  default     = "10.20.1.0/24"
}

variable "availability_zone" {
  description = "Zona de disponibilidade utilizada inicialmente."
  type        = string
  default     = "us-east-1a"
}

variable "instance_type" {
  description = "Tipo da instancia EC2 utilizada inicialmente pelo cluster EcoCiente."
  type        = string
  default     = "t3.large"
}

variable "root_volume_size" {
  description = "Tamanho do volume raiz da EC2 em GB."
  type        = number
  default     = 30
}

variable "instance_name" {
  description = "Nome da instancia EC2 principal."
  type        = string
  default     = "ecociente-k3s-server"
}