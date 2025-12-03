variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Function deployment"
  type        = string
}

variable "content_bucket_name" {
  description = "Names of content buckets"
  type        = string
}

variable "function_name" {
  description = "Name of the Cloud Function"
  type        = string
  default     = "list-bucket-objects"
}
