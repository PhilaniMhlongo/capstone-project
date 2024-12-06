from datetime import datetime
import os
import json
import boto3
from aws_lambda_powertools import Logger, Tracer

# Globals
logger = Logger()
tracer = Tracer(service="StorageApp")
storage_units_table = os.getenv('STORAGE_UNITS_TABLE')
rentals_table = os.getenv('RENTALS_TABLE')
access_log_table = os.getenv('ACCESS_LOG_TABLE')
dynamodb = boto3.resource('dynamodb')
units_table = dynamodb.Table(storage_units_table)
rentals_table = dynamodb.Table(rentals_table)
access_log_table = dynamodb.Table(access_log_table)
sns = boto3.client('sns')

@tracer.capture_method
def update_unit_status(event, context):
    """
    Update storage unit status (for support staff)
    """
    logger.info("Updating storage unit status")
    
    detail = json.loads(event['body'])
    unit_id = detail['unit_id']
    new_status = detail['status']
    
    valid_statuses = ['Available', 'Unavailable', 'Reserved', 'Cancelling', 'Problem']
    if new_status not in valid_statuses:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid status"})
        }
    
    units_table.update_item(
        Key={'unit_id': unit_id},
        UpdateExpression='SET status = :status',
        ExpressionAttributeValues={
            ':status': new_status
        }
    )
    
    logger.info(f"Unit {unit_id} status updated to {new_status}")
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Unit status updated"})
    }

@tracer.capture_method
def share_unit_access(event, context):
    """
    Share storage unit access with another user
    """
    logger.info("Sharing storage unit access")
    
    detail = json.loads(event['body'])
    rental_id = detail['rental_id']
    shared_user_id = detail['shared_user_id']
    start_date = detail.get('start_date')
    end_date = detail.get('end_date')
    
    # Validate rental
    rental_response = rentals_table.get_item(
        Key={'rental_id': rental_id}
    )
    rental = rental_response.get('Item')
    
    if not rental:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Rental not found"})
        }
    
    # Add shared access record
    access_log_table.put_item(
        Item={
            'rental_id': rental_id,
            'shared_user_id': shared_user_id,
            'start_date': start_date,
            'end_date': end_date,
            'status': 'Active'
        }
    )
    
    logger.info(f"Access to unit shared with user {shared_user_id}")
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Access shared successfully"})
    }

@tracer.capture_method
def log_unit_access(event, context):
    """
    Log and notify when a storage unit is accessed
    """
    logger.info("Logging unit access")
    
    detail = json.loads(event['body'])
    unit_id = detail['unit_id']
    user_id = event['requestContext']['authorizer']['claims']['sub']
    
    # Log access
    access_log_table.put_item(
        Item={
            'unit_id': unit_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }
    )
    
    # Notify owner
    rental_response = rentals_table.get_item(
        Key={'unit_id': unit_id}
    )
    rental = rental_response.get('Item')
    
    if rental:
        sns.publish(
            TopicArn=os.getenv('UNIT_ACCESS_NOTIFICATION_TOPIC'),
            Message=f"Your storage unit {unit_id} was accessed at {datetime.now().isoformat()}"
        )
    
    logger.info(f"Unit {unit_id} access logged and notification sent")
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Access logged"})
    }

@tracer.capture_lambda_handler
def lambda_handler(event, context):
    try:
        operation = event['httpMethod']
        if operation == 'PUT' and 'status' in json.loads(event['body']):
            return update_unit_status(event, context)
        elif operation == 'POST' and 'shared_user_id' in json.loads(event['body']):
            return share_unit_access(event, context)
        elif operation == 'POST' and 'unit_id' in json.loads(event['body']):
            return log_unit_access(event, context)
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid operation"})
            }
    except Exception as err:
        logger.exception(err)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(err)})
        }
        