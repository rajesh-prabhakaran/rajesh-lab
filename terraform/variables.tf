variable "s3_bucket_name" {
  description = "Name of the existing S3 bucket containing the Lambda ZIP"
  type        = string
}

variable "s3_object_key" {
  description = "Key (path) to the Lambda ZIP file in the S3 bucket"
  type        = string
}
