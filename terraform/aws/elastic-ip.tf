resource "aws_eip" "k3s" {
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-k3s-eip"
  }
}

resource "aws_eip_association" "k3s" {
  instance_id   = aws_instance.k3s_server.id
  allocation_id = aws_eip.k3s.id
}
