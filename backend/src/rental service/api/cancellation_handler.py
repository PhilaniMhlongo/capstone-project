import boto3
import json
import os
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
eventbridge = boto3.client('events')
ses = boto3.client('ses')

def lambda_handler(event, context):
    """
    Handle rental cancellation workflows triggered by EventBridge
    
    Expected event structure:
    {
        "source": "self-storage.rentals",
        "detail-type": "RentalCancellationRequested",
        "detail": {
            "rentalId": "string",
            "customerId": "string",
            "reason": "string",
            "cancellationDate": "ISO8601 timestamp"
        }
    }
    """
    try:
        # Validate incoming event
        if not event or 'detail' not in event:
            raise ValueError("Invalid event structure")
        
        detail = event['detail']
        rental_id = detail.get('rentalId')
        customer_id = detail.get('customerId')
        
        if not rental_id or not customer_id:
            raise ValueError("Missing required rental or customer ID")
        
        # Retrieve rental information
        rentals_table = dynamodb.Table(os.environ['RENTALS_TABLE'])
        rental_response = rentals_table.get_item(
            Key={
                'RentalId': rental_id,
                'CustomerId': customer_id
            }
        )
        
        if 'Item' not in rental_response:
            raise ValueError(f"Rental {rental_id} not found")
        
        rental = rental_response['Item']
        
        # Determine cancellation eligibility and fees
        cancellation_result = process_cancellation(rental)
        
        # Update rental status in DynamoDB
        update_rental_status(rentals_table, rental_id, customer_id, cancellation_result)
        
        # Send notification to customer
        send_cancellation_notification(customer_id, cancellation_result)
        
        return {
            'statusCode': 200,
            'body': json.dumps(cancellation_result)
        }
    
    except Exception as e:
        # Log error and send error notification
        print(f"Cancellation Error: {str(e)}")
        send_error_notification(str(e))
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Cancellation processing failed',
                'details': str(e)
            })
        }

def process_cancellation(rental):
    """
    Calculate cancellation eligibility and potential fees
    """
    start_date = datetime.fromisoformat(rental['StartDate'])
    current_date = datetime.now()
    rental_duration = (start_date - current_date).days
    
    # Cancellation policy rules
    if rental_duration > 30:  # More than 30 days notice
        fee_percentage = 0
    elif rental_duration > 15:  # 15-30 days notice
        fee_percentage = 0.25
    elif rental_duration > 7:  # 7-15 days notice
        fee_percentage = 0.5
    else:  # Less than 7 days notice
        fee_percentage = 0.75
    
    total_rental_cost = rental.get('TotalCost', 0)
    cancellation_fee = total_rental_cost * fee_percentage
    
    return {
        'rentalId': rental['RentalId'],
        'status': 'Cancelled',
        'cancellationDate': datetime.now().isoformat(),
        'refundAmount': total_rental_cost - cancellation_fee,
        'cancellationFee': cancellation_fee,
        'feePercentage': fee_percentage
    }

def update_rental_status(table, rental_id, customer_id, cancellation_result):
    """
    Update rental status in DynamoDB
    """
    table.update_item(
        Key={
            'RentalId': rental_id,
            'CustomerId': customer_id
        },
        UpdateExpression="SET CancellationStatus = :status, RefundAmount = :refund, CancellationFee = :fee",
        ExpressionAttributeValues={
            ':status': cancellation_result['status'],
            ':refund': cancellation_result['refundAmount'],
            ':fee': cancellation_result['cancellationFee']
        }
    )

def send_cancellation_notification(customer_id, cancellation_result):
    """
    Send SES email notification about cancellation
    """
    ses.send_email(
        Source=os.environ.get('NOTIFICATION_EMAIL', 'noreply@yourstorage.com'),
        Destination={'ToAddresses': [get_customer_email(customer_id)]},
        Message={
            'Subject': {'Data': 'Rental Cancellation Confirmation'},
            'Body': {
                'Text': {
                    'Data': f"""
                    Rental Cancellation Details:
                    - Rental ID: {cancellation_result['rentalId']}
                    - Cancellation Date: {cancellation_result['cancellationDate']}
                    - Refund Amount: ${cancellation_result['refundAmount']:.2f}
                    - Cancellation Fee: ${cancellation_result['cancellationFee']:.2f}
                    """
                }
            }
        }
    )

def get_customer_email(customer_id):
    """
    Retrieve customer email from Cognito or another user management system
    """
    # Implement customer email retrieval logic
    # This is a placeholder - replace with actual user lookup
    return f"{customer_id}@example.com"

def send_error_notification(error_message):
    """
    Send error notification to support team
    """
    ses.send_email(
        Source=os.environ.get('ERROR_NOTIFICATION_EMAIL', 'support@yourstorage.com'),
        Destination={'ToAddresses': ['support@yourstorage.com']},
        Message={
            'Subject': {'Data': 'Rental Cancellation Error'},
            'Body': {
                'Text': {
                    'Data': f"An error occurred during rental cancellation: {error_message}"
                }
            }
        }
    )