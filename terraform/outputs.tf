output "function_url" {
  description = "URL of the Cloud Function"
  value       = google_cloudfunctions2_function.list_bucket_objects.service_config[0].uri
}

output "load_balancer_ip" {
  description = "IP address of the load balancer"
  value       = google_compute_global_address.default.address
}

output "load_balancer_url" {
  description = "HTTP URL of the load balancer"
  value       = "http://${google_compute_global_address.default.address}"
}
