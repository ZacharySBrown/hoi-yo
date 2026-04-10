output "public_ip" {
  description = "Public IP address of the hoi-yo server"
  value       = aws_spot_instance_request.hoi_yo.public_ip
}

output "dashboard_url" {
  description = "URL for the hoi-yo dashboard"
  value       = "http://${aws_spot_instance_request.hoi_yo.public_ip}:8080"
}

output "ssh_command" {
  description = "SSH command to connect to the server"
  value       = "ssh -i ~/.ssh/${var.ssh_key_name}.pem ubuntu@${aws_spot_instance_request.hoi_yo.public_ip}"
}

output "next_steps" {
  description = "Post-deploy instructions"
  value       = <<-EOT

    ============================================================
    hoi-yo server is launching on a spot instance.

    1. Set your real secrets (if you haven't yet):
       aws ssm put-parameter --name /hoi-yo/steam-user --value "YOUR_USER" --type SecureString --overwrite
       aws ssm put-parameter --name /hoi-yo/steam-pass --value "YOUR_PASS" --type SecureString --overwrite
       aws ssm put-parameter --name /hoi-yo/anthropic-api-key --value "sk-..." --type SecureString --overwrite
       aws ssm put-parameter --name /hoi-yo/dashboard-password-hash --value "..." --type SecureString --overwrite
       aws ssm put-parameter --name /hoi-yo/jwt-secret --value "..." --type SecureString --overwrite

    2. Dashboard: http://${aws_spot_instance_request.hoi_yo.public_ip}:8080

    3. SSH:      ssh -i ~/.ssh/${var.ssh_key_name}.pem ubuntu@${aws_spot_instance_request.hoi_yo.public_ip}

    4. Logs:     sudo journalctl -u hoi-yo -f
    ============================================================
  EOT
}
