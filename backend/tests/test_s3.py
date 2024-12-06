from unittest.mock import patch
import boto3
import pytest

@patch("boto3.client")
def test_s3(mock_boto_client):
    # Set up mock S3 client
    mock_s3 = mock_boto_client.return_value
    
    # Mock create_bucket
    mock_s3.create_bucket(Bucket="my-test-bucket")
    
    # Mock the response for list_buckets()
    mock_s3.list_buckets.return_value = {
        'Buckets': [{'Name': 'my-test-bucket'}],
        'Owner': {'DisplayName': 'owner', 'ID': 'owner-id'}
    }

    # Call the list_buckets method and validate the response
    response = mock_s3.list_buckets()
    assert "my-test-bucket" in [bucket['Name'] for bucket in response['Buckets']]
