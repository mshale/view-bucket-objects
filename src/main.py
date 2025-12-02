"""GCP Cloud Function to list objects from a Cloud Storage bucket."""

import functions_framework
from flask import jsonify
from google.cloud import storage


@functions_framework.http
def list_bucket_objects(request):
    """HTTP Cloud Function to list objects from a GCS bucket with pagination.

    Args:
        request (flask.Request): The request object.
            Query parameters:
                - bucket_name (str): Required. Name of the GCS bucket.
                - page_token (str): Optional. Token for pagination.
                - max_results (int): Optional. Maximum results per page (default 1000).

    Returns:
        flask.Response: JSON response with object names, sizes, and next page token.
            Example response:
            {
                "objects": [
                    {"name": "file001.txt", "size": 1234},
                    {"name": "file002.txt", "size": 4321}
                ],
                "next_page_token": "ABC123"
            }
    """
    # Handle CORS preflight request
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }
        return ("", 204, headers)

    # Set CORS headers for the main request
    headers = {"Access-Control-Allow-Origin": "*"}

    # Get query parameters
    bucket_name = request.args.get("bucket_name")
    if not bucket_name:
        return (
            jsonify({"error": "Missing required parameter: bucket_name"}),
            400,
            headers,
        )

    page_token = request.args.get("page_token")
    max_results = request.args.get("max_results", 1000, type=int)

    # Limit max_results to 1000
    if max_results > 1000:
        max_results = 1000

    try:
        # Initialize the Cloud Storage client
        client = storage.Client()

        # Get the bucket
        bucket = client.bucket(bucket_name)

        # List objects with pagination
        blobs = client.list_blobs(
            bucket,
            max_results=max_results,
            page_token=page_token,
        )

        # Build the response
        objects = []
        for blob in blobs:
            objects.append({"name": blob.name, "size": blob.size})

        # Get the next page token
        next_page_token = blobs.next_page_token

        response_data = {"objects": objects}

        if next_page_token:
            response_data["next_page_token"] = next_page_token

        return (jsonify(response_data), 200, headers)

    except Exception as e:
        return (
            jsonify({"error": str(e)}),
            500,
            headers,
        )
