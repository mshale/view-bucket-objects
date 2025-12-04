resource "google_cloud_run_service" "not_found_backend" {
  name     = "not-found-backend"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/404-server"
        ports {
          container_port = 8080
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_member" "cloudrun_invoker" {
  service  = google_cloud_run_service.not_found_backend.name
  location = google_cloud_run_service.not_found_backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# resource "google_compute_backend_service" "not_found_backend" {
#   name                  = "not-found-backend"
#   protocol              = "HTTP"
#   timeout_sec           = 30
#   backend {
#     group = google_cloud_run_service.not_found_backend.status[0].url
#   }
# }