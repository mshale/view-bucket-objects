# view-bucket-objects

Serve GCP bucket objects via an HTTP Endpoint backed by a GCP Cloud Function and Load Balancer.

## Overview

This project provides an HTTP endpoint served by a GCP HTTP Load Balancer that fronts a GCP Cloud Function. The Cloud Function uses the GCP Python client library to query a Cloud Storage bucket and return stored objects in JSON format.

Important change: this project now exposes a single Cloud Function entry point compatible with Google Cloud Functions Gen 2 and the Functions Framework. The function is implemented in src/main.py as the function `list_bucket_objects` and is decorated with `@functions_framework.http`. 

### Prerequisites

- Terraform >= 1.0.0
- GCP Project with billing enabled
- `gcloud` CLI configured with appropriate permissions
- Python runtime compatible with Cloud Functions (e.g., python310)

## Features

- **Cloud Function HTTP Entry Point**: `list_bucket_objects` decorated with `@functions_framework.http`
- **Pagination Support**: Returns up to 1000 objects per request with pagination tokens
- **JSON Response**: Returns object names and sizes in a structured JSON format
- **CORS support**: Responds to OPTIONS preflight and includes CORS headers on responses

## API Response Format

```json
{
  "objects": [
    {"name": "file001.txt", "size": 1234},
    {"name": "file002.txt", "size": 4321}
  ],
  "next_page_token": "ABC123"
}
```

## API Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `bucket_name` | string | Yes (or set BUCKET_NAME env var) | Name of the GCS bucket to query |
| `page_token` | string | No | Token for pagination (from previous response) |
| `max_results` | integer | No | Maximum results per page (default: 1000, max: 1000) |

## Usage Examples

When deployed behind the Load Balancer or invoked directly, the function accepts query parameters on the request URL.

List objects from a bucket:
```bash
curl "http://<load-balancer-or-function-url>/function/get-objects"
```

<!-- Paginate through results:
```bash
# First request
curl "http://<load-balancer-or-function-url>/?bucket_name=my-bucket&max_results=100"

# Next page using token from previous response
curl "http://<load-balancer-or-function-url>/?bucket_name=my-bucket&max_results=100&page_token=ABC123"
``` -->

## Deployment

Create a bucket on GCP to store the temporary txt files, you can then generate random files locally and push them to the GCP cloud storage bucket.

```bash
export PROJECT_ID=your-project-id
export BUCKET_NAME=your-bucket-name
mkdir -p sample_files
for i in $(seq -w 1 2000); do head -c $((RANDOM+1000)) /dev/urandom > "sample_files/file${i}.txt"; done
gsutil -m cp sample_files/*.txt gs://YOUR_BUCKET_NAME/
```

### Enable the required GCP APIs

- Cloud Functions API
- Cloud Run API (if used by Terraform templates)
- Cloud Storage API
- Compute Engine API (for Load Balancer resources)

### Terraform notes

Ensure your Cloud Function resource's entry point is set to:
```hcl
entry_point = "list_bucket_objects"
```
and that you're deploying the package containing `src/main.py` and `requirements.txt`.

## Development

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

2. Run locally with the Functions Framework (recommended for testing the actual function entry point):
```bash
# from project root
functions-framework --target=list_bucket_objects --source=src --port=8080
# then:
curl "http://127.0.0.1:8080/?bucket_name=my-bucket"
```

### Terraform installation

To install terraform templates follow the steps below, first install the cloudrun, this will work as the default backend for the loadbalancer and returns a 404 if a different path is used.

```bash
# authentication
gcloud auth configure-docker

# Build the image
docker build -t gcr.io/PROJECT_ID/404-server .

# Push to Google Container Registry
docker push gcr.io/PROJECT_ID/404-server

# Deploy to Cloud Run
gcloud run deploy not-found-server \
  --image gcr.io/PROJECT_ID/404-server \
  --platform managed \
  --region REGION \
  --allow-unauthenticated

# Please note if running this on Mac and the above fails, please use cloudbuild to build and push the container.
gcloud builds submit --tag gcr.io/${PROJECT_ID}/404-server
```
After installing the above run terraform init and terraform apply to install the terraform resources

```bash
terraform init
terraform plan -out tfplan
terraform apply "tfplan"
```

Notes:
- The Functions Framework exposes the same entry point and request behavior used in Cloud Functions, including handling decorated function invocation and routing.
- The function responds to OPTIONS preflight requests for CORS.

### Run Tests

Unit tests are in the tests/ directory and import the function implementation from src.main. Tests are adjusted to call the original (undecorated) function logic where necessary:

```bash
PYTHONPATH=src pytest tests/test_main.py -v
```

You can run a single test:
```bash
PYTHONPATH=src pytest tests/test_main.py -v -k "test_list_objects_success"
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │     │                 │
│     Client      │────▶│  HTTP Load      │────▶│ Cloud Function  │────▶│  Cloud Storage  │
│                 │     │   Balancer      │     │  (list_bucket_  │     │     Bucket      │
│                 │     │                 │     │   objects)      │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
```

## File Structure

```
.
├── src/
│   └── main.py             # Cloud Function code (entry point: list_bucket_objects)
├── requirements.txt        # Python dependencies (functions-framework, google-cloud-storage)
├── requirements-dev.txt    # Development dependencies (pytest, mock, etc.)
├── tests/
│   └── test_main.py        # Unit tests
├── README.md               # This file
├── app.py
├── Dockerfile
└── terraform/
    ├── provider.tf
    ├── variables.tf
    ├── outputs.tf
    ├── cloud_function.tf
    ├── cloud_run.tf
    └── load_balancer.tf
```

## License

MIT