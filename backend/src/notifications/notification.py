import boto3
import json
import os

ses = boto3.client('ses')
sns = boto3.client('sns')

def lambda_handler(event, context):
    """
    Central notification handling service triggered by EventBridge
    
    Supports multiple notification types:
    - Unit status changes
    - Security alerts
    - General system notifications
    """
    try:
        # Validate event structure
        if not event or 'detail-type' not in event:
            raise ValueError("Invalid event structure")
        
        detail_type = event['detail-type']
        detail = event.get('detail', {})
        
        # Route notification based on event type
        if detail_type == 'UnitStatusChanged':
            handle_unit_status_notification(detail)
        elif detail_type == 'SecurityAlert':
            handle_security_notification(detail)
        else:
            handle_generic_notification(detail_type, detail)
        
        return {
            'statusCode': 200,
            'body': json.dumps(f'Processed {detail_type} notification')
        }
    
    except Exception as e:
        print(f"Notification Error: {str(e)}")
        send_error_notification(str(e))
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Notification processing failed',
                'details': str(e)
            })
        }

def handle_unit_status_notification(detail):
    """
    Process and send notifications for unit status changes
    """
    customer_email = get_customer_email(detail['customerId'])
    
    # Different notification based on status
    status_messages = {
        'Available': "Your storage unit is now available for booking.",
        'Reserved': "Your storage unit has been reserved.",
        'Unavailable': "Your storage unit is currently unavailable.",
        'Problem': "There's an issue with your storage unit that requires attention."
    }
    
    message = status_messages.get(detail['newStatus'], 'Unit status update')
    
    send_email_notification(
        to_email=customer_email,
        subject=f"Storage Unit {detail['unitId']} Status Update",
        body=f"""
        Unit {detail['unitId']} Status Update
        
        {message}
        
        Details:
        - Previous Status: {detail.get('previousStatus', 'N/A')}
        - New Status: {detail['newStatus']}
        """
    )
    
    # Optional: Send SMS if customer prefers
    send_sms_notification(
        phone_number=get_customer_phone(detail['customerId']),
        message=f"Unit {detail['unitId']} is now {detail['newStatus']}"
    )

def handle_security_notification(detail):
    """
    Process and send security-related notifications
    """
    # High-priority security notifications
    admin_emails = ['security@yourstorage.com', 'admin@yourstorage.com']
    
    for admin_email in admin_emails:
        send_email_notification(
            to_email=admin_email,
            subject="Security Alert for Storage Facility",
            body=f"""
            Security Alert Detected
            
            Type: {detail.get('alertType', 'Unknown')}
            Location: {detail.get('facilityId')}"""
        )