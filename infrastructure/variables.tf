variable "yc_token" {
  type        = string
  description = "IAM token"
}

variable "cloud_id" {
  type = string
}

variable "folder_id" {
  type = string
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "s3_access_key" {
  type      = string
  sensitive = true
}

variable "s3_secret_key" {
  type      = string
  sensitive = true
}
