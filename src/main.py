"""GCP Cloud Function to list objects from a Cloud Storage bucket."""

from flask import Flask, request, jsonify
from google.cloud import storage
import os

app = Flask(__name__)

def list_bucket_objects(request):
    """
    List objects in a Google Cloud Storage bucket via HTTP GET request.

    Parameters:
        request (flask.Request): The HTTP request object. Expects the following query parameters:
            - bucket_name (str, required): Name of the GCS bucket. Can also be set via BUCKET_NAME environment variable.
            - page_token (str, optional): Token for pagination to retrieve the next set of results.
            - max_results (int, optional): Maximum number of objects to return (default: 2000, capped at 10).

    Returns:
        flask.Response: JSON response with the following format:
            {
                "objects": [
                    {"name": "<object_name>", "size": <object_size>},
                    ...
                ],
                "next_page_token": "<token>"  # Only present if more results are available
            }
        On error, returns:
            {
                "error": "<error_message>"
            }
        All responses include CORS headers.

    Example:
        GET /function/get-objects?bucket_name=my-bucket&max_results=5
        Response:
        {
            "objects": [
                {"name": "file1.txt", "size": 1234},
                {"name": "file2.txt", "size": 5678}
            ],
            "next_page_token": "abc123"
        }
    """
    headers = {"Access-Control-Allow-Origin": "*"}
    bucket_name = request.args.get("bucket_name") or os.environ.get("BUCKET_NAME")
    if not bucket_name:
        return (
            jsonify({"error": "Missing required parameter: bucket_name"}),
            400,
            headers,
        )

    page_token = request.args.get("page_token")
    max_results = request.args.get("max_results", 2000, type=int)
    if max_results > 10:
        max_results = 10

    project_id = os.environ.get("PROJECT_ID")

    try:
        if project_id:
            client = storage.Client(project=project_id)
        else:
            client = storage.Client()
        bucket = client.bucket(bucket_name)
        blobs_iter = client.list_blobs(
            bucket,
            max_results=max_results,
            page_token=page_token,
        )
        objects = [{"name": blob.name, "size": blob.size} for blob in blobs_iter]
        next_page_token = getattr(blobs_iter, "next_page_token", None)
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

@app.route("/function/get-objects", methods=["GET"])
def list_bucket_objects_route():
    return list_bucket_objects(request)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return jsonify({"error": "Not Found"}), 404

if __name__ == "__main__":
    app.run(debug=True)