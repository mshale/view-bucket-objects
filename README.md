# view-bucket-objects

Serve GCP bucket objects via an HTTP Endpoint backed by a GCP Cloud Function and Load Balancer.

## Overview

This project provides an HTTP endpoint served by a GCP HTTP Load Balancer that fronts a GCP Cloud Function. The Cloud Function uses the GCP Python client library to query a Cloud Storage bucket and return stored objects in JSON format.

## Features

- **HTTP Endpoint**: Accessible via GCP HTTP Load Balancer
- **Pagination Support**: Returns up to 1000 objects per request with pagination tokens
- **JSON Response**: Returns object names and sizes in a structured JSON format

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
| `bucket_name` | string | Yes | Name of the GCS bucket to query |
| `page_token` | string | No | Token for pagination (from previous response) |
| `max_results` | integer | No | Maximum results per page (default: 1000, max: 1000) |

## Usage Examples

### List objects from a bucket

```bash
curl "http://<load-balancer-ip>/?bucket_name=my-bucket"
```

### Paginate through results

```bash
# First request
curl "http://<load-balancer-ip>/?bucket_name=my-bucket&max_results=100"

# Next page using token from previous response
curl "http://<load-balancer-ip>/?bucket_name=my-bucket&max_results=100&page_token=ABC123"
```

## Deployment

Create a bucket on GCP to store the temporary txt files, you can then generate random files locally and push them to the GCP cloud storage bucket.

```bash
export PROJECT_ID=your-project_id
export BUCKET_NAME=Your-bucket-name
mkdir -p sample_files
for i in $(seq -w 1 2000); do head -c $((RANDOM+1000)) /dev/urandom > "sample_files/file${i}.txt"; done
gsutil -m cp sample_files/*.txt gs://YOUR_BUCKET_NAME/
```

### Prerequisites

- Terraform >= 1.0.0
- GCP Project with billing enabled
- `gcloud` CLI configured with appropriate permissions

### Deploy with Terraform

1. Navigate to the terraform directory:

```bash
cd terraform
```

2. Create a `terraform.tfvars` file:

```hcl
project_id  = "your-gcp-project-id"
content_bucket_name = "your-bucket-to-query"
region              = "europe-west2"
```
3. Initialize Terraform:

```bash
terraform init
```

4. Apply the configuration:

```bash
terraform apply
```

5. After deployment, get the load balancer URL:

```bash
terraform output load_balancer_url
```

### Required GCP APIs

- Cloud Functions API
- Cloud Run API
- Cloud Storage API
- Compute Engine API

## Development

### Local Development

1. Install dependencies:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

2. Test locally:

```bash
python main.py

curl "http://127.0.0.1:5000/function/get-objects"
```

### Run Tests

```bash
PYTHON=/src pytest tests/test_main.py -v

PYTHON=/src pytest tests/test_main.py -v -k "test_list_objects_success"
```

<!-- ### Run Tests with Coverage

```bash
PYTHON=/src pytest tests/test_main.py -v --cov=main --cov-report=term-missing
``` -->

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │     │                 │
│     Client      │────▶│  HTTP Load      │────▶│ Cloud Function  │────▶│  Cloud Storage  │
│                 │     │   Balancer      │     │                 │     │     Bucket      │
│                 │     │                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
```

## File Structure

```
.
├── main.py                 # Cloud Function code
├── requirements.txt        # Python dependencies
├── requirements-dev.txt    # Development dependencies
├── test_main.py           # Unit tests
├── README.md              # This file
└── terraform/
    ├── provider.tf            # Provider configuration
    ├── variables.tf       # Input variables
    ├── outputs.tf         # Output values
    ├── cloud_function.tf  # Cloud Function resources
    └── load_balancer.tf   # Load Balancer resources
```

## License

MIT
