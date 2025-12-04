"""GCP Cloud Function to list objects from a Cloud Storage bucket.

This version exposes a single HTTP function compatible with Cloud Functions Gen 2:
- Uses @functions_framework.http decorator so the Functions Framework (and GCF runtime)
  can discover and invoke the function.
- Handles CORS preflight (OPTIONS).
- Reads BUCKET_NAME and PROJECT_ID from environment if not provided via query.
- Returns JSON with objects and optional next_page_token.
"""

import os
import functions_framework
from flask import Request, jsonify
from google.cloud import storage


@functions_framework.http
def list_bucket_objects(request: Request):
    # CORS headers
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
    }

    # Respond to CORS preflight
    if request.method == "OPTIONS":
        return ("", 204, headers)

    # Query params and env fallbacks
    bucket_name = request.args.get("bucket_name") or os.environ.get("BUCKET_NAME")
    if not bucket_name:
        return (jsonify({"error": "Missing required parameter: bucket_name"}), 400, headers)

    page_token = request.args.get("page_token")
    try:
        max_results = int(request.args.get("max_results", "1000"))
    except (ValueError, TypeError):
        return (jsonify({"error": "max_results must be an integer"}), 400, headers)

    # cap max_results to a reasonable number
    if max_results > 1000:
        max_results = 1000

    project_id = os.environ.get("PROJECT_ID")

    try:
        client = storage.Client(project=project_id) if project_id else storage.Client()
        # list_blobs accepts bucket name or bucket object
        blobs_iter = client.list_blobs(
            bucket_name,
            max_results=max_results,
            page_token=page_token,
        )

        objects = [{"name": blob.name, "size": blob.size} for blob in blobs_iter]

        # HTTPIterator in google-cloud-storage exposes next_page_token on the iterator in many versions
        next_page_token = getattr(blobs_iter, "next_page_token", None)

        response_data = {"objects": objects}
        if next_page_token:
            response_data["next_page_token"] = next_page_token

        return (jsonify(response_data), 200, headers)
    except Exception as e:
        # Return error and include CORS headers for client handling
        return (jsonify({"error": str(e)}), 500, headers)