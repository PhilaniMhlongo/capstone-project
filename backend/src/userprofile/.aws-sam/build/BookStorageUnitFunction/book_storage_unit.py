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
    logger.info("Booking storage unit")
    
    detail = event['detail']
    user_id = event['requestContext']['authorizer']['claims']['sub']
    
    unit_id = detail['unit_id']
    rental_duration = detail['duration']
    billing_option = detail['billingOption']
    
    # Check unit availability
    unit_response = units_table.get_item(
        Key={'unit_id': unit_id}
    )
    unit = unit_response.get('Item')
    
    if not unit or unit['status'] != 'Available':
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Unit not available"})
        }
    
    # Calculate rental details
    rental_id = str(uuid.uuid4())
    start_date = datetime.now()
    
    if rental_duration == 'indefinite':
        end_date = None
    else:
        duration_map = {
            '1day': 1, 
            '1month': 30, 
            '6months': 180, 
            '1year': 365
        }
        days = duration_map.get(rental_duration, 30)
        end_date = start_date + timedelta(days=days)
    
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
    key = {"unit_id": {"S": unit_id}}  # Replace with actual unit_id

    # Update Expression
    update_expression = "SET #status = :status_val"
    expression_attribute_names = {"#status": "status"}  # Dynamically reference the 'status' attribute
    expression_attribute_values = {":status_val": {"S": "occupied"}}  # New value for 'status'

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
        "statusCode": 200,
        "body": json.dumps({
            "rental_id": rental_id,
            "unit_id": unit_id
        })
    }


def lambda_handler(event, context):
    return book_storage_unit(event, context)
  