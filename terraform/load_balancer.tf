# Reserve a global external IP address for the load balancer
resource "google_compute_global_address" "default" {
  name = "${var.function_name}-ip"
}

# Create a serverless NEG for the Cloud Function
resource "google_compute_region_network_endpoint_group" "function_neg" {
  name                  = "${var.function_name}-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_function {
    function = google_cloudfunctions2_function.list_bucket_objects.name
  }
}

# Create a backend service
resource "google_compute_backend_service" "default" {
  name        = "${var.function_name}-backend"
  protocol    = "HTTP"
  port_name   = "http"
  timeout_sec = 30

  backend {
    group = google_compute_region_network_endpoint_group.function_neg.id
  }
}

# Create a URL map
resource "google_compute_url_map" "default" {
  name            = "${var.function_name}-url-map"
  default_service = google_compute_backend_service.default.id
}

# Create a target HTTP proxy
resource "google_compute_target_http_proxy" "default" {
  name    = "${var.function_name}-http-proxy"
  url_map = google_compute_url_map.default.id
}

# Create a global forwarding rule
resource "google_compute_global_forwarding_rule" "default" {
  name       = "${var.function_name}-forwarding-rule"
  target     = google_compute_target_http_proxy.default.id
  port_range = "80"
  ip_address = google_compute_global_address.default.address
}
