import json
import os
import uuid
from datetime import datetime, timedelta
import boto3

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

def validate_booking_input(body):
    """
    Validate the input for booking a storage unit.
    """
    required_fields = ['facilityId', 'unitId', 'startDate', 'endDate']
    
    # Check for missing required fields
    for field in required_fields:
        if field not in body:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate date format and duration
    try:
        start_date = datetime.fromisoformat(body['startDate'])
        end_date = datetime.fromisoformat(body['endDate'])
    except ValueError:
        raise ValueError("Invalid date format. Use ISO format (YYYY-MM-DD)")
    
    # Minimum 1 day rental
    if (end_date - start_date).days < 1:
        raise ValueError("Minimum rental period is 1 day")
    
    # Maximum rental period (e.g., 5 years)
    max_rental_period = timedelta(days=365 * 5)
    if (end_date - start_date) > max_rental_period:
        raise ValueError("Maximum rental period is 5 years")
    
    return start_date, end_date

def lambda_handler(event, context):
    """
    Lambda handler for booking a storage unit.
    """
    try:
        # Validate environment variable
        table_name = os.environ.get('TABLE_NAME')
        if not table_name:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Environment variable TABLE_NAME is not set'})
            }
        
        table = dynamodb.Table(table_name)
        
        # Parse input
        if not event.get('body'):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing request body'})
            }
        
        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid JSON'})
            }
        
        # Validate input
        try:
            start_date, end_date = validate_booking_input(body)
        except ValueError as ve:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': str(ve)})
            }
        
        # Generate unique rental ID
        rental_id = str(uuid.uuid4())
        
        # Check unit availability
        try:
            response = table.get_item(
                Key={
                    'facilityId': body['facilityId'],
                    'unitId': body['unitId']
                }
            )
        except Exception as e:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to check unit availability',
                    'details': str(e)
                })
            }
        
        # Verify unit is available
        unit = response.get('Item')
        if not unit or unit.get('status') != 'Available':
            return {
                'statusCode': 409,
                'body': json.dumps({'error': 'Storage unit is not available'})
            }
        
        # Prepare rental item
        rental_item = {
            'facilityId': body['facilityId'],
            'unitId': body['unitId'],
            'rentalId': rental_id,
            'userId': body['userId'],
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat(),
            'status': 'Available',
            'createdAt': datetime.utcnow().isoformat(),
            'expirationTime': int(end_date.timestamp())  # DynamoDB TTL attribute
        }
        
        # Optional: Add additional fields
        if 'additionalDetails' in body:
            rental_item['additionalDetails'] = body['additionalDetails']
        
        # Write rental to DynamoDB
        try:
            table.put_item(
                Item=rental_item,
                ConditionExpression='attribute_not_exists(rentalId)'
            )
        except Exception as e:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to book storage unit',
                    'details': str(e)
                })
            }
        
        # Update unit status
        try:
            table.update_item(
                Key={
                    'facilityId': body['facilityId'],
                    'unitId': body['unitId']
                },
                UpdateExpression='SET #status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'Reserved'},
                ConditionExpression='attribute_exists(unitId)'
            )
        except Exception as e:
            print(f"Failed to update unit status: {e}")
        
        # Return successful response
        return {
            'statusCode': 201,
            'body': json.dumps({
                'message': 'Storage unit booked successfully',
                'rentalId': rental_id,
                'unitId': body['unitId'],
                'startDate': start_date.isoformat(),
                'endDate': end_date.isoformat()
            })
        }
    
    except Exception as e:
        # Catch any unexpected errors
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Unexpected error occurred',
                'details': str(e)
            })
        }
