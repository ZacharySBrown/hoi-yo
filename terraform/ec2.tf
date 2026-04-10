resource "aws_spot_instance_request" "hoi_yo" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  spot_price             = var.spot_max_price
  wait_for_fulfillment   = true
  spot_type              = "one-time"
  key_name               = var.ssh_key_name
  vpc_security_group_ids = [aws_security_group.hoi_yo.id]
  iam_instance_profile   = aws_iam_instance_profile.hoi_yo.name

  user_data = file("${path.module}/userdata.sh")

  root_block_device {
    volume_size           = var.volume_size
    volume_type           = "gp3"
    delete_on_termination = true
  }

  tags = {
    Name    = "hoi-yo-server"
    Project = "hoi-yo"
  }
}
