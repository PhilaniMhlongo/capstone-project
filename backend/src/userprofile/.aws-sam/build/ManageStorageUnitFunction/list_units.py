import json
import os
import traceback
import logging
import uuid
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, Key

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')

def generate_error_id():
    """Generate a unique error tracking ID."""
    return str(uuid.uuid4())

def lambda_handler(event, context):
    # Generate a unique request ID for tracing
    request_id = generate_error_id()
    
    try:
        # Log incoming event for debugging
        logger.info(f"Request ID: {request_id}")
        logger.info(f"Incoming Event: {json.dumps(event)}")
        
        # Extract query parameters with robust parsing
        query_params = event.get('queryStringParameters', {}) or {}
        
        # Validate and set parameters with default values and type checking
        try:
            status = query_params.get('status')
            page = max(1, int(query_params.get('page', 1)))
            limit = max(1, min(int(query_params.get('limit', 10)), 100))  # Limit between 1-100
        except (TypeError, ValueError) as param_error:
            logger.error(f"Parameter parsing error - Request ID: {request_id}")
            logger.error(f"Error details: {str(param_error)}")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid query parameters',
                    'request_id': request_id,
                    'details': str(param_error)
                })
            }

        # Verify required environment variables
        table_name = os.environ.get('STORAGE_UNITS_TABLE')
        if not table_name:
            logger.error(f"Missing table name environment variable - Request ID: {request_id}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Configuration error',
                    'request_id': request_id,
                    'details': 'Missing DynamoDB table name'
                })
            }

        # Prepare DynamoDB table
        try:
            table = dynamodb.Table(table_name)
        except ClientError as table_error:
            logger.error(f"Table access error - Request ID: {request_id}")
            logger.error(f"Error details: {str(table_error)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Database access error',
                    'request_id': request_id,
                    'details': str(table_error)
                })
            }

        # Prepare query parameters
        query_kwargs = {
            'Limit': limit
        }

        # Add filter if status is provided
        if status:
            query_kwargs['FilterExpression'] = Attr('availabilityStatus').eq(status)

        # Attempt to retrieve items
        try:
            response = table.scan(**query_kwargs)
            
            # Log query performance
            logger.info(f"Query stats - Request ID: {request_id}")
            logger.info(f"Items scanned: {response.get('ScannedCount', 0)}")
            logger.info(f"Items returned: {len(response.get('Items', []))}")
        except ClientError as query_error:
            logger.error(f"Query execution error - Request ID: {request_id}")
            logger.error(f"Error details: {str(query_error)}")
            logger.error(traceback.format_exc())
            
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Database query failed',
                    'request_id': request_id,
                    'details': str(query_error)
                })
            }

        # Process and return results
        units = response.get('Items', [])
        
        # Detailed response with debugging information
        return {
            'statusCode': 200,
            'body': json.dumps({
                'request_id': request_id,
                'units': units,
                'total': len(units),
                'page': page,
                'limit': limit,
                'status_filter': status or 'None',
                'debug_info': {
                    'scanned_count': response.get('ScannedCount', 0),
                    'last_evaluated_key': response.get('LastEvaluatedKey')
                }
            })
        }

    except Exception as unexpected_error:
        # Catch-all for any unexpected errors
        logger.error(f"Unexpected error - Request ID: {request_id}")
        logger.error(f"Error details: {str(unexpected_error)}")
        logger.error(traceback.format_exc())
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Unexpected server error',
                'request_id': request_id,
                'details': str(unexpected_error)
            })
        }