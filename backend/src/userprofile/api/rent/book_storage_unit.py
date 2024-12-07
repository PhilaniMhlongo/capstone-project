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

# Constants for validation
VALID_DURATIONS = {'1day', '1month', '6months', '1year', 'indefinite'}
VALID_BILLING_OPTIONS = {'monthly', 'annually', 'prepaid'}

@tracer.capture_method
def validate_booking_request(detail):
    """
    Validate the booking request parameters
    """
    # Check required fields
    required_fields = ['unit_id', 'duration', 'billingOption']
    for field in required_fields:
        if field not in detail:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate duration
    if detail['duration'] not in VALID_DURATIONS:
        raise ValueError(f"Invalid duration. Must be one of {VALID_DURATIONS}")
    
    # Validate billing option
    if detail['billingOption'] not in VALID_BILLING_OPTIONS:
        raise ValueError(f"Invalid billing option. Must be one of {VALID_BILLING_OPTIONS}")

@tracer.capture_method
def book_storage_unit(event, context):
    """
    Book a storage unit with flexible rental options
    """
    try:
        logger.info("Booking storage unit")
        
        # Extract user and booking details
        detail = event['detail']
        user_id = event['requestContext']['authorizer']['claims']['sub']
        
        # Validate input
        validate_booking_request(detail)
        
        unit_id = detail['unit_id']
        rental_duration = detail['duration']
        billing_option = detail['billingOption']
        
        # Check unit availability
        unit_response = units_table.get_item(
            Key={'unit_id': unit_id}
        )
        unit = unit_response.get('Item')
        
        if not unit or unit['availabilityStatus'] != 'Available':
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Unit not available"})
            }
        
        # Calculate rental details
        rental_id = str(uuid.uuid4())
        start_date = datetime.now()
        
        # Calculate end date based on duration
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
        
        # Update unit status using the correct method
        units_table.update_item(
            Key={'unit_id': unit_id},
            UpdateExpression='SET availabilityStatus = :status',
            ExpressionAttributeValues={
                ':status': 'Reserved'
            },
            ReturnValues='UPDATED_NEW'
        )
        
        logger.info(f"Storage unit {unit_id} booked by user {user_id}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "rental_id": rental_id,
                "unit_id": unit_id
            })
        }
    
    except ValueError as ve:
        logger.error(f"Validation Error: {str(ve)}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(ve)})
        }
    except Exception as e:
        logger.error(f"Unexpected error booking storage unit: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }

def lambda_handler(event, context):
    return book_storage_unit(event, context)