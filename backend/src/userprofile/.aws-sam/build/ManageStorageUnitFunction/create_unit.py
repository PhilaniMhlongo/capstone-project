import json
import os
import uuid
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
cognito_idp = boto3.client('cognito-idp')

def lambda_handler(event, context):
    # Verify user is an admin
    try:
        # Extract the user ID from the request context
        user_id = event['requestContext']['authorizer']['claims']['sub']
        
        # Check if user is an admin
        claims = event['requestContext']['authorizer']['claims']
    
        # Check if user is in admin group
        if 'cognito:groups' not in claims or 'Admins' not in claims['cognito:groups']:
            return {
                'statusCode': 403,
                'body': json.dumps({'error': 'Unauthorized: Admin access required'})
            }
        
        # Parse request body
        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid request body'})
            }
        
        # Validate input
        required_fields = ['location', 'size', 'imgUrl', 'availabilityStatus']
        for field in required_fields:
            if field not in body:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }
        
        # Generate unique unit ID
        unit_id = str(uuid.uuid4())
        
        # Prepare item for DynamoDB
        unit_item = {
            'unit_id': unit_id,
            'location': body['location'],
            'size': body['size'],
            'imgUrl': body['imgUrl'],
            'availabilityStatus': body['availabilityStatus']
        }
        
        # Store in DynamoDB
        table = dynamodb.Table(os.environ['STORAGE_UNITS_TABLE'])
        table.put_item(Item=unit_item)
        
        return {
            'statusCode': 201,
            'body': json.dumps(unit_item)
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }