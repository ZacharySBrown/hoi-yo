# SSM Parameter Store secrets for hoi-yo.
#
# These are created with placeholder values. Set the real values manually:
#   aws ssm put-parameter --name /hoi-yo/steam-user      --value "YOUR_USER"  --type SecureString --overwrite
#   aws ssm put-parameter --name /hoi-yo/steam-pass      --value "YOUR_PASS"  --type SecureString --overwrite
#   aws ssm put-parameter --name /hoi-yo/anthropic-api-key --value "sk-..."   --type SecureString --overwrite
#   aws ssm put-parameter --name /hoi-yo/dashboard-password-hash --value "..."  --type SecureString --overwrite
#   aws ssm put-parameter --name /hoi-yo/jwt-secret      --value "..."        --type SecureString --overwrite

resource "aws_ssm_parameter" "steam_user" {
  name  = "/hoi-yo/steam-user"
  type  = "SecureString"
  value = "PLACEHOLDER"

  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Project = "hoi-yo"
  }
}

resource "aws_ssm_parameter" "steam_pass" {
  name  = "/hoi-yo/steam-pass"
  type  = "SecureString"
  value = "PLACEHOLDER"

  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Project = "hoi-yo"
  }
}

resource "aws_ssm_parameter" "anthropic_api_key" {
  name  = "/hoi-yo/anthropic-api-key"
  type  = "SecureString"
  value = "PLACEHOLDER"

  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Project = "hoi-yo"
  }
}

resource "aws_ssm_parameter" "dashboard_password_hash" {
  name  = "/hoi-yo/dashboard-password-hash"
  type  = "SecureString"
  value = "PLACEHOLDER"

  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Project = "hoi-yo"
  }
}

resource "aws_ssm_parameter" "jwt_secret" {
  name  = "/hoi-yo/jwt-secret"
  type  = "SecureString"
  value = "PLACEHOLDER"

  lifecycle {
    ignore_changes = [value]
  }

  tags = {
    Project = "hoi-yo"
  }
}
