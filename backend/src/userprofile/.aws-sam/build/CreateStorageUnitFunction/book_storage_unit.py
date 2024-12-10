import os
import uuid
import json
import traceback
import boto3
from datetime import datetime, timedelta
from aws_lambda_powertools import Logger, Tracer

# Globals
logger = Logger()
tracer = Tracer(service="StorageApp")
storage_units_table = os.getenv('STORAGE_UNITS_TABLE')
rentals_table = os.getenv('RENTALS_TABLE')
RENTAL_EVENTS_QUEUE = os.getenv('RENTAL_EVENTS_QUEUE')

dynamodb = boto3.resource('dynamodb')
sqs_client = boto3.client('sqs')
# Enhanced logging configuration
logger.setLevel('INFO')

# Constants for validation
VALID_DURATIONS = {'1day', '1month', '6months', '1year', 'indefinite'}
VALID_BILLING_OPTIONS = {'monthly', 'annually', 'prepaid'}

@tracer.capture_method
def validate_booking_request(detail):
    """
    Validate the booking request parameters with enhanced error details
    """
    # Comprehensive field validation
    required_fields = ['unit_id', 'duration', 'billingOption']
    for field in required_fields:
        if field not in detail or not detail.get(field):
            raise ValueError(f"Missing required field: {field}")
    
    # Detailed validation with specific error messages
    if detail['duration'] not in VALID_DURATIONS:
        raise ValueError(
            f"Invalid duration '{detail['duration']}'. "
            f"Must be one of {', '.join(VALID_DURATIONS)}"
        )
    
    if detail['billingOption'] not in VALID_BILLING_OPTIONS:
        raise ValueError(
            f"Invalid billing option '{detail['billingOption']}'. "
            f"Must be one of {', '.join(VALID_BILLING_OPTIONS)}"
        )

@tracer.capture_method
def book_storage_unit(event, context):
    """
    Book a storage unit with comprehensive error handling and logging
    """
    try:
        # Log the full event for debugging
        logger.info(f"Raw event: {json.dumps(event)}")
        
        # Parse the body if it's a string (API Gateway often passes body as string)
        if isinstance(event, str):
            try:
                event = json.loads(event)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON in event")
        
        # Handle different event structures
        detail = event
        if 'body' in event:
            # Try to parse body if it's a JSON string
            try:
                detail = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            except (json.JSONDecodeError, TypeError):
                detail = event
        
        # Log parsed detail for debugging
        logger.info(f"Parsed detail: {json.dumps(detail)}")
        
        # Extract user ID from context (modify as needed based on your auth setup)
        user_id = (event.get('requestContext', {})
                   .get('authorizer', {})
                   .get('claims', {})
                   .get('sub'))
        
        # Fallback user ID if not found
        if not user_id:
            # You might want to replace this with a more appropriate fallback or error handling
            user_id = 'unknown_user'
        
        # Validate input with enhanced error handling
        validate_booking_request(detail)
        
        unit_id = detail['unit_id']
        rental_duration = detail['duration']
        billing_option = detail['billingOption']
        
        # Rest of the function remains the same as in the previous version
        # (DynamoDB operations, rental creation, etc.)
        
        # Enhanced DynamoDB error handling
        try:
            units_table_instance = dynamodb.Table(storage_units_table)
            rentals_table_instance = dynamodb.Table(rentals_table)
        except Exception as db_error:
            logger.error(f"DynamoDB table initialization error: {str(db_error)}")
            raise RuntimeError("Failed to connect to database")
        
        # Check unit availability with detailed logging
        try:
            unit_response = units_table_instance.get_item(
                Key={'unit_id': unit_id}
            )
        except Exception as fetch_error:
            logger.error(f"Error fetching unit details: {str(fetch_error)}")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Database query failed",
                    "details": str(fetch_error)
                })
            }
        
        unit = unit_response.get('Item')
        
        if not unit or unit['availabilityStatus'] != 'Available':
            logger.warning(f"Unit {unit_id} not available. Current status: {unit.get('availabilityStatus', 'Unknown')}")
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Unit not available",
                    "unit_status": unit.get('availabilityStatus', 'Unknown')
                })
            }
        
        # Calculate rental details with UTC timestamp
        rental_id = str(uuid.uuid4())
        start_date = datetime.utcnow()
        
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
        
        # Create rental record with comprehensive error handling
        try:
            rentals_table_instance.put_item(
                Item={
                    'rental_id': rental_id,
                    'unit_id': unit_id,
                    'user_id': user_id,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat() if end_date else None,
                    'billing_option': billing_option,
                    'availabilityStatus': 'Reserved'
                }
            )
        except Exception as put_error:
            logger.error(f"Error creating rental record: {str(put_error)}")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Failed to create rental record",
                    "details": str(put_error)
                })
            }
        
        # Update unit status with error handling
        try:
            units_table_instance.update_item(
                Key={'unit_id': unit_id},
                UpdateExpression='SET availabilityStatus = :status',
                ExpressionAttributeValues={
                    ':status': 'Reserved'
                },
                ReturnValues='UPDATED_NEW'
            )
        except Exception as update_error:
            logger.error(f"Error updating unit status: {str(update_error)}")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Failed to update unit status",
                    "details": str(update_error)
                })
            }
        # Publish booking event
        publish_booking_event({
            'unit_id': unit_id,
            'user_id': user_id,
            'rental_id': rental_id
        })
        
        logger.info(f"Storage unit {unit_id} booked by user {user_id}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "rental_id": rental_id,
                "unit_id": unit_id,
                "message": "Booking successful"
            })
        }
    
    except ValueError as ve:
        logger.error(f"Validation Error: {str(ve)}")
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Validation failed",
                "details": str(ve)
            })
        }
    except Exception as e:
        # Comprehensive error logging
        logger.error(f"Unexpected error booking storage unit: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "details": str(e),
                "traceback": traceback.format_exc()
            })
        }

def lambda_handler(event, context):
    return book_storage_unit(event, context)


@tracer.capture_method
def publish_booking_event(booking_details):
    """Publish an event to the SQS queue for downstream processing."""
    try:
        sqs_client.send_message(
            QueueUrl=RENTAL_EVENTS_QUEUE,
            MessageBody=json.dumps({
                'detail-type': 'rental.booking.requested',
                'detail': {
                    'unit_id': booking_details['unit_id'],
                    'user_id': booking_details['user_id'],
                    'rental_id': booking_details['rental_id'],
                    'booking_date': datetime.utcnow().isoformat()
                }
            })
        )
        logger.info(f"Published booking event for rental {booking_details['rental_id']}")
    except Exception as e:
        logger.error(f"Failed to publish booking event: {e}")
        raise