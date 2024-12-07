import os
import uuid
import json
import boto3
from datetime import datetime, timedelta
from aws_lambda_powertools import Logger, Tracer

# Globals
logger = Logger()
tracer = Tracer(service="StorageApp")
storage_units_table = os.getenv('STORAGE_UNITS_TABLE')
rentals_table = os.getenv('RENTALS_TABLE')
dynamodb = boto3.resource('dynamodb')
units_table = dynamodb.Table(storage_units_table)
rentals_table = dynamodb.Table(rentals_table)

@tracer.capture_method
def book_storage_unit(event, context):
    """
    Book a storage unit with flexible rental options
    """
    logger.info("Raw Event Received", extra={"event": event})
    
    try:
        # Extract user_id
        if 'requestContext' not in event or 'authorizer' not in event['requestContext']:
            logger.error("Missing authorization context")
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Unauthorized: Missing authentication context"})
            }
        
        user_id = event['requestContext']['authorizer']['claims']['sub']
        logger.info(f"User ID: {user_id}")
        
        # Parse request body
        if 'body' not in event:
            logger.error("Missing request body")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing request body"})
            }
        
        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid JSON in request body"})
            }
        
        # Validate required fields
        required_fields = ['unit_id', 'duration', 'billingOption']
        for field in required_fields:
            if field not in body:
                logger.error(f"Missing required field: {field}")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": f"Missing required field: {field}"})
                }
        
        unit_id = body['unit_id']
        rental_duration = body['duration']
        billing_option = body['billingOption']
        
        # Check unit availability
        unit_response = units_table.get_item(
            Key={'unit_id': unit_id}
        )
        unit = unit_response.get('Item')
        
        if not unit:
            logger.error(f"Unit not found: {unit_id}")
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Unit not found"})
            }
        
        if unit.get('availabilityStatus') != 'Available':
            logger.error(f"Unit not available: {unit_id}, Status: {unit.get('availabilityStatus')}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Unit not available"})
            }
        
        # Calculate rental details
        rental_id = str(uuid.uuid4())
        start_date = datetime.now()
        
        duration_map = {
            '1day': 1, 
            '1month': 30, 
            '6months': 180, 
            '1year': 365,
            'indefinite': None
        }
        
        if rental_duration not in duration_map:
            logger.error(f"Invalid rental duration: {rental_duration}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid rental duration"})
            }
        
        days = duration_map.get(rental_duration)
        end_date = start_date + timedelta(days=days) if days is not None else None
        
        # Create rental record
        rentals_table.put_item(
            Item={
                'rental_id': rental_id,
                'unit_id': unit_id,
                'user_id': user_id,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat() if end_date else None,
                'billing_option': billing_option,
                'status': 'Reserved'
            }
        )
        
        # Update unit status
        key = {"unit_id": {"S": unit_id}}

        # Update Expression
        update_expression = "SET #status = :status_val"
        expression_attribute_names = {"#status": "availabilityStatus"}
        expression_attribute_values = {":status_val": {"S": "Reserved"}}

        # Update the item
        dynamodb.update_item(
            TableName=storage_units_table,
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="UPDATED_NEW"
        )
            
        logger.info(f"Storage unit {unit_id} booked by user {user_id}")
        
        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "rental_id": rental_id,
                "unit_id": unit_id
            })
        }
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }

def lambda_handler(event, context):
    return book_storage_unit(event, context)