variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type (needs 4+ vCPUs for HOI4)"
  type        = string
  default     = "c6i.xlarge"
}

variable "spot_max_price" {
  description = "Maximum hourly price for the spot instance in USD"
  type        = string
  default     = "0.06"
}

variable "ssh_key_name" {
  description = "Name of an existing EC2 key pair for SSH access"
  type        = string
}

variable "volume_size" {
  description = "Root EBS volume size in GB (HOI4 + OS + saves)"
  type        = number
  default     = 60
}

variable "admin_ip" {
  description = "Your public IP address for SSH access (CIDR, e.g. 1.2.3.4/32)"
  type        = string
}

variable "domain_name" {
  description = "Optional domain name for HTTPS (leave empty to skip cert setup)"
  type        = string
  default     = ""
}
