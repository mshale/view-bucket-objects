# Create a GCS bucket for the Cloud Function source code
resource "google_storage_bucket" "function_source" {
  name                        = "${var.project_id}-function-source"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
}

# Archive the function source code
data "archive_file" "function_source" {
  type        = "zip"
  output_path = "${path.module}/function-source.zip"

  source {
    content  = file("${path.module}/../main.py")
    filename = "main.py"
  }

  source {
    content  = file("${path.module}/../requirements.txt")
    filename = "requirements.txt"
  }
}

# Upload the function source code to GCS
resource "google_storage_bucket_object" "function_source" {
  name   = "function-source-${data.archive_file.function_source.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.function_source.output_path
}

# Create the Cloud Function (Gen 2)
resource "google_cloudfunctions2_function" "list_bucket_objects" {
  name        = var.function_name
  location    = var.region
  description = "HTTP function to list objects from a GCS bucket"

  build_config {
    runtime     = "python311"
    entry_point = "list_bucket_objects"
    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.function_source.name
      }
    }
  }

  service_config {
    max_instance_count    = 10
    min_instance_count    = 0
    available_memory      = "256M"
    timeout_seconds       = 60
    service_account_email = google_service_account.function_sa.email

    environment_variables = {
      BUCKET_NAME = var.bucket_name
    }

    ingress_settings               = "ALLOW_ALL"
    all_traffic_on_latest_revision = true
  }

  depends_on = [google_service_account.function_sa]
}

# Allow public access to the Cloud Function
resource "google_cloud_run_service_iam_member" "invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.list_bucket_objects.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Create a service account for the Cloud Function
resource "google_service_account" "function_sa" {
  account_id   = "list-bucket-objects-sa"
  display_name = "Service account for list-bucket-objects function"
}

# Grant the service account read access to the target bucket
resource "google_storage_bucket_iam_member" "bucket_reader" {
  bucket = var.bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.function_sa.email}"
}
