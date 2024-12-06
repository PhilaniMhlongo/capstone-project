import boto3
import os
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

def lambda_handler(event, context):
    """
    Scheduled function to send payment reminders for upcoming and overdue rentals
    """
    try:
        # Retrieve active rentals with upcoming/overdue payments
        rentals = get_rentals_needing_reminder()
        
        # Process and send reminders
        for rental in rentals:
            send_payment_reminder(rental)
        
        return {
            'statusCode': 200,
            'body': f'Sent {len(rentals)} payment reminders'
        }
    
    except Exception as e:
        print(f"Payment Reminder Error: {str(e)}")
        send_error_notification(str(e))
        
        return {
            'statusCode': 500,
            'body': f'Error processing payment reminders: {str(e)}'
        }

def get_rentals_needing_reminder():
    """
    Query DynamoDB for rentals requiring payment reminders
    """
    rentals_table = dynamodb.Table(os.environ['RENTALS_TABLE'])
    
    # Get current and upcoming dates
    now = datetime.now()
    upcoming_week = now + timedelta(days=7)
    
    # Query for rentals with upcoming or overdue payments
    response = rentals_table.scan(
        FilterExpression=(
            "PaymentStatus = :unpaid AND " +
            "(NextPaymentDate <= :upcoming_week OR NextPaymentDate < :now)"
        ),
        ExpressionAttributeValues={
            ':unpaid': 'UNPAID',
            ':now': now.isoformat(),
            ':upcoming_week': upcoming_week.isoformat()
        }
    )
    
    return response.get('Items', [])

def send_payment_reminder(rental):
    """
    Send payment reminder email to customer
    """
    customer_id = rental['CustomerId']
    email = get_customer_email(customer_id)
    
    # Determine reminder type based on payment status
    if is_payment_overdue(rental):
        reminder_type = "OVERDUE"
        subject = "Urgent: Payment Overdue for Your Storage Unit"
        body = create_overdue_reminder_body(rental)
    else:
        reminder_type = "UPCOMING"
        subject = "Upcoming Payment for Your Storage Unit"
        body = create_upcoming_reminder_body(rental)
    
    # Send email
    ses.send_email(
        Source=os.environ.get('NOTIFICATION_EMAIL', 'billing@yourstorage.com'),
        Destination={'ToAddresses': [email]},
        Message={
            'Subject': {'Data': subject},
            'Body': {'Text': {'Data': body}}
        }
    )
    
    # Log reminder
    log_payment_reminder(rental, reminder_type)

def is_payment_overdue(rental):
    """
    Check if payment is overdue
    """
    next_payment_date = datetime.fromisoformat(rental['NextPaymentDate'])
    return next_payment_date < datetime.now()

def create_upcoming_reminder_body(rental):
    """
    Generate reminder email body for upcoming payment
    """
    return f"""
    Dear Storage Unit Customer,

    A friendly reminder that your next payment of ${rental['NextPaymentAmount']:.2f} 
    is due on {rental['NextPaymentDate']}.

    Rental Details:
    - Rental ID: {rental['RentalId']}
    - Unit: {rental['UnitId']}
    - Payment Due: {rental['NextPaymentDate']}
    - Amount: ${rental['NextPaymentAmount']:.2f}

    Please ensure timely payment to avoid service interruption.

    Best regards,
    Your Storage Team
    """

def create_overdue_reminder_body(rental):
    """
    Generate reminder email body for overdue payment
    """
    return f"""
    URGENT: Payment Overdue

    Dear Storage Unit Customer,

    This is to notify you that your payment for Storage Unit {rental['UnitId']} 
    is OVERDUE by {calculate_overdue_days(rental)} days.

    Overdue Details:
    - Rental ID: {rental['RentalId']}
    - Overdue Amount: ${rental['NextPaymentAmount']:.2f}
    - Originally Due: {rental['NextPaymentDate']}

    Immediate action required to prevent:
    1. Late fees
    2. Service interruption
    3. Potential unit lock-out

    Please make payment immediately to restore your account to good standing.

    Best regards,
    Your Storage Team
    """

def calculate_overdue_days(rental):
    """
    Calculate number of days payment is overdue
    """
    next_payment_date = datetime.fromisoformat(rental['NextPaymentDate'])
    return (datetime.now() - next_payment_date).days

def get_customer_email(customer_id):
    """
    Retrieve customer email 
    (Replace with actual customer lookup mechanism)
    """
    return f"{customer_id}@example.com"

def log_payment_reminder(rental, reminder_type):
    """
    Log payment reminder event 
    (Could be extended to log in CloudWatch or another tracking system)
    """
    print(f"Payment {reminder_type} Reminder sent for Rental {rental['RentalId']}")

def send_error_notification(error_message):
    """
    Send error notification to support team
    """
    ses.send_email(
        Source=os.environ.get('ERROR_NOTIFICATION_EMAIL', 'support@yourstorage.com'),
        Destination={'ToAddresses': ['support@yourstorage.com']},
        Message={
            'Subject': {'Data': 'Payment Reminder System Error'},
            'Body': {
                'Text': {
                    'Data': f"An error occurred in the payment reminder system: {error_message}"
                }
            }
        }
    )