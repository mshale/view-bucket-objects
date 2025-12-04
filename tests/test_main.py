import json
from unittest.mock import MagicMock, patch
import os
from flask import Flask
from werkzeug.datastructures import ImmutableMultiDict

from src.main import list_bucket_objects

app = Flask(__name__)

class MockBlob:
    def __init__(self, name, size):
        self.name = name
        self.size = size

class MockBlobIterator:
    def __init__(self, blobs, next_page_token=None):
        self._blobs = blobs
        self.next_page_token = next_page_token

    def __iter__(self):
        return iter(self._blobs)

def create_mock_request(args=None):
    mock_request = MagicMock()
    mock_request.args = ImmutableMultiDict(args or {})
    mock_request.method = "GET"
    mock_request.path = "/function/get-objects"
    return mock_request

class TestListBucketObjects:
    def test_missing_bucket_name(self):
        with app.app_context():
            os.environ.pop("BUCKET_NAME", None)
            request = create_mock_request({})
            # The function in src.main is decorated with @functions_framework.http.
            # Call the original wrapped function for unit testing via __wrapped__.
            response = list_bucket_objects.__wrapped__(request)
            response_data, status_code, headers = response
            response_json = json.loads(response_data.get_data(as_text=True))
            assert status_code == 400
            assert response_json["error"] == "Missing required parameter: bucket_name"

    @patch("src.main.storage.Client")
    def test_list_objects_success(self, mock_client_class):
        with app.app_context():
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_blobs = [MockBlob("file001.txt", 1234), MockBlob("file002.txt", 4321)]
            mock_blob_iterator = MockBlobIterator(mock_blobs)
            mock_client.list_blobs.return_value = mock_blob_iterator
            request = create_mock_request({"bucket_name": "test-bucket"})
            response = list_bucket_objects.__wrapped__(request)
            response_data, status_code, headers = response
            response_json = json.loads(response_data.get_data(as_text=True))
            assert status_code == 200
            assert "objects" in response_json
            assert len(response_json["objects"]) == 2
            assert response_json["objects"][0]["name"] == "file001.txt"
            assert response_json["objects"][0]["size"] == 1234
            assert response_json["objects"][1]["name"] == "file002.txt"
            assert response_json["objects"][1]["size"] == 4321
            assert "next_page_token" not in response_json

    @patch("src.main.storage.Client")
    def test_list_objects_with_pagination(self, mock_client_class):
        with app.app_context():
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_blobs = [MockBlob("file001.txt", 1234)]
            mock_blob_iterator = MockBlobIterator(mock_blobs, next_page_token="ABC123")
            mock_client.list_blobs.return_value = mock_blob_iterator

            request = create_mock_request({"bucket_name": "test-bucket"})
            response = list_bucket_objects.__wrapped__(request)
            response_data, status_code, headers = response
            response_json = json.loads(response_data.get_data(as_text=True))

            assert status_code == 200
            assert "objects" in response_json
            assert len(response_json["objects"]) == 1
            assert response_json["objects"][0]["name"] == "file001.txt"
            assert response_json["objects"][0]["size"] == 1234
            assert response_json["next_page_token"] == "ABC123"
            assert headers["Access-Control-Allow-Origin"] == "*"