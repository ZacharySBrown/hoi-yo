data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "hoi_yo" {
  name               = "hoi-yo-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json

  tags = {
    Project = "hoi-yo"
  }
}

data "aws_iam_policy_document" "ssm_read" {
  statement {
    sid    = "ReadHoiYoParams"
    effect = "Allow"

    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
    ]

    resources = [
      "arn:aws:ssm:${var.aws_region}:*:parameter/hoi-yo/*",
    ]
  }
}

resource "aws_iam_role_policy" "ssm_read" {
  name   = "hoi-yo-ssm-read"
  role   = aws_iam_role.hoi_yo.id
  policy = data.aws_iam_policy_document.ssm_read.json
}

resource "aws_iam_instance_profile" "hoi_yo" {
  name = "hoi-yo-instance-profile"
  role = aws_iam_role.hoi_yo.name
}
