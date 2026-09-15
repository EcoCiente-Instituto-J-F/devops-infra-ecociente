output "vpc_id" {
  description = "ID da VPC do EcoCiente."
  value       = aws_vpc.ecociente.id
}

output "public_subnet_id" {
  description = "ID da subnet publica."
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "ID do Security Group principal."
  value       = aws_security_group.ecociente.id
}

output "ec2_instance_id" {
  description = "ID da instancia EC2 principal."
  value       = aws_instance.k3s_server.id
}

output "ec2_public_ip" {
  description = "IPv4 publico estatico da instancia."
  value       = aws_eip.k3s.public_ip
}

output "ec2_private_ip" {
  description = "IPv4 privado da instancia."
  value       = aws_instance.k3s_server.private_ip
}