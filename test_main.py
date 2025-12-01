"""Unit tests for the list_bucket_objects Cloud Function."""

import json
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from werkzeug.datastructures import ImmutableMultiDict

from main import list_bucket_objects


# Create Flask app for testing context
app = Flask(__name__)


class MockBlob:
    """Mock GCS Blob object."""

    def __init__(self, name, size):
        self.name = name
        self.size = size


class MockBlobIterator:
    """Mock iterator for blobs with pagination support."""

    def __init__(self, blobs, next_page_token=None):
        self._blobs = blobs
        self.next_page_token = next_page_token
        self._index = 0

    def __iter__(self):
        return iter(self._blobs)


def create_mock_request(args=None, method="GET"):
    """Create a mock Flask request object."""
    mock_request = MagicMock()
    mock_request.args = ImmutableMultiDict(args or {})
    mock_request.method = method
    return mock_request


class TestListBucketObjects:
    """Test cases for list_bucket_objects function."""

    def test_missing_bucket_name(self):
        """Test that missing bucket_name returns 400 error."""
        with app.app_context():
            request = create_mock_request({})
            response_data, status_code, headers = list_bucket_objects(request)
            response_json = json.loads(response_data.get_data(as_text=True))

            assert status_code == 400
            assert "error" in response_json
            assert "bucket_name" in response_json["error"]

    def test_cors_preflight(self):
        """Test CORS preflight request handling."""
        with app.app_context():
            request = create_mock_request(method="OPTIONS")
            response_data, status_code, headers = list_bucket_objects(request)

            assert status_code == 204
            assert headers["Access-Control-Allow-Origin"] == "*"
            assert "GET" in headers["Access-Control-Allow-Methods"]

    @patch("main.storage.Client")
    def test_list_objects_success(self, mock_client_class):
        """Test successful listing of bucket objects."""
        with app.app_context():
            # Setup mock
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_blobs = [
                MockBlob("file001.txt", 1234),
                MockBlob("file002.txt", 4321),
            ]
            mock_blob_iterator = MockBlobIterator(mock_blobs)

            mock_client.list_blobs.return_value = mock_blob_iterator

            # Create request
            request = create_mock_request({"bucket_name": "test-bucket"})

            # Call function
            response_data, status_code, headers = list_bucket_objects(request)
            response_json = json.loads(response_data.get_data(as_text=True))

            # Assertions
            assert status_code == 200
            assert "objects" in response_json
            assert len(response_json["objects"]) == 2
            assert response_json["objects"][0]["name"] == "file001.txt"
            assert response_json["objects"][0]["size"] == 1234
            assert response_json["objects"][1]["name"] == "file002.txt"
            assert response_json["objects"][1]["size"] == 4321
            assert "next_page_token" not in response_json

    @patch("main.storage.Client")
    def test_list_objects_with_pagination(self, mock_client_class):
        """Test listing objects with pagination token."""
        with app.app_context():
            # Setup mock
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_blobs = [
                MockBlob("file001.txt", 1234),
            ]
            mock_blob_iterator = MockBlobIterator(mock_blobs, next_page_token="ABC123")

            mock_client.list_blobs.return_value = mock_blob_iterator

            # Create request
            request = create_mock_request({"bucket_name": "test-bucket"})

            # Call function
            response_data, status_code, headers = list_bucket_objects(request)
            response_json = json.loads(response_data.get_data(as_text=True))

            # Assertions
            assert status_code == 200
            assert "objects" in response_json
            assert "next_page_token" in response_json
            assert response_json["next_page_token"] == "ABC123"

    @patch("main.storage.Client")
    def test_list_objects_with_page_token(self, mock_client_class):
        """Test listing objects using a provided page token."""
        with app.app_context():
            # Setup mock
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_blobs = [MockBlob("file003.txt", 5678)]
            mock_blob_iterator = MockBlobIterator(mock_blobs)

            mock_client.list_blobs.return_value = mock_blob_iterator

            # Create request with page token
            request = create_mock_request({
                "bucket_name": "test-bucket",
                "page_token": "ABC123"
            })

            # Call function
            response_data, status_code, headers = list_bucket_objects(request)
            response_json = json.loads(response_data.get_data(as_text=True))

            # Verify the page token was passed to list_blobs
            mock_client.list_blobs.assert_called_once()
            call_kwargs = mock_client.list_blobs.call_args[1]
            assert call_kwargs["page_token"] == "ABC123"

            assert status_code == 200

    @patch("main.storage.Client")
    def test_max_results_limit(self, mock_client_class):
        """Test that max_results is capped at 1000."""
        with app.app_context():
            # Setup mock
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_blobs = []
            mock_blob_iterator = MockBlobIterator(mock_blobs)
            mock_client.list_blobs.return_value = mock_blob_iterator

            # Create request with max_results > 1000
            request = create_mock_request({
                "bucket_name": "test-bucket",
                "max_results": "5000"
            })

            # Call function
            list_bucket_objects(request)

            # Verify max_results was capped at 1000
            mock_client.list_blobs.assert_called_once()
            call_kwargs = mock_client.list_blobs.call_args[1]
            assert call_kwargs["max_results"] == 1000

    @patch("main.storage.Client")
    def test_custom_max_results(self, mock_client_class):
        """Test that custom max_results is respected when <= 1000."""
        with app.app_context():
            # Setup mock
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_blobs = []
            mock_blob_iterator = MockBlobIterator(mock_blobs)
            mock_client.list_blobs.return_value = mock_blob_iterator

            # Create request with max_results = 500
            request = create_mock_request({
                "bucket_name": "test-bucket",
                "max_results": "500"
            })

            # Call function
            list_bucket_objects(request)

            # Verify max_results was set correctly
            mock_client.list_blobs.assert_called_once()
            call_kwargs = mock_client.list_blobs.call_args[1]
            assert call_kwargs["max_results"] == 500

    @patch("main.storage.Client")
    def test_error_handling(self, mock_client_class):
        """Test error handling when GCS client fails."""
        with app.app_context():
            # Setup mock to raise an exception
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.list_blobs.side_effect = Exception("Bucket not found")

            # Create request
            request = create_mock_request({"bucket_name": "nonexistent-bucket"})

            # Call function
            response_data, status_code, headers = list_bucket_objects(request)
            response_json = json.loads(response_data.get_data(as_text=True))

            # Assertions
            assert status_code == 500
            assert "error" in response_json
            assert "Bucket not found" in response_json["error"]

    @patch("main.storage.Client")
    def test_empty_bucket(self, mock_client_class):
        """Test listing objects from an empty bucket."""
        with app.app_context():
            # Setup mock
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_blobs = []
            mock_blob_iterator = MockBlobIterator(mock_blobs)
            mock_client.list_blobs.return_value = mock_blob_iterator

            # Create request
            request = create_mock_request({"bucket_name": "empty-bucket"})

            # Call function
            response_data, status_code, headers = list_bucket_objects(request)
            response_json = json.loads(response_data.get_data(as_text=True))

            # Assertions
            assert status_code == 200
            assert "objects" in response_json
            assert len(response_json["objects"]) == 0
            assert "next_page_token" not in response_json

    def test_cors_headers_on_success(self):
        """Test that CORS headers are set on successful responses."""
        with app.app_context():
            with patch("main.storage.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                mock_blobs = []
                mock_blob_iterator = MockBlobIterator(mock_blobs)
                mock_client.list_blobs.return_value = mock_blob_iterator

                request = create_mock_request({"bucket_name": "test-bucket"})
                _, _, headers = list_bucket_objects(request)

                assert headers["Access-Control-Allow-Origin"] == "*"

    def test_cors_headers_on_error(self):
        """Test that CORS headers are set on error responses."""
        with app.app_context():
            request = create_mock_request({})
            _, _, headers = list_bucket_objects(request)

            assert headers["Access-Control-Allow-Origin"] == "*"
