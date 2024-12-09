import os
import json
import uuid
from datetime import datetime, timedelta
import boto3
from aws_lambda_powertools import Logger, Tracer

# Globals
logger = Logger()
tracer = Tracer(service="StorageApp")
rentals_table = os.getenv('RENTALS_TABLE')
payments_table = os.getenv('PAYMENTS_TABLE')
unit_table = os.getenv('UNIT_TABLE')
dynamodb = boto3.resource('dynamodb')
rentals_table = dynamodb.Table(rentals_table)
payments_table = dynamodb.Table(payments_table)
unit_table = dynamodb.Table(unit_table)

@tracer.capture_method
def manage_payment_method(event, context):
    """
    Add or update customer payment method
    """
    logger.info("Managing payment method")
    logger.info(f"Incoming event: {json.dumps(event)}")

    
    detail = json.loads(event['body'])
    user_id = event['requestContext']['authorizer']['claims']['sub']
    
   


    payments_table.put_item(
        Item={
            'user_id': user_id,
            'payment_id': str(uuid.uuid4()),
            'type': detail.get('type', 'card'),  # card or eft
            'last_four_digits': detail.get('last_four_digits', 'XXXX'),
            'created_at': datetime.now().isoformat()
        }
    )
    
    logger.info(f"Payment method added for user {user_id}")
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Payment method added"})
    }

@tracer.capture_method
def process_pre_payment(event, context):
    """
    Process pre-payment for storage unit rental
    """
    logger.info("Processing pre-payment")
    
    detail = json.loads(event['body'])
    user_id = event['requestContext']['authorizer']['claims']['sub']
    unit_id = detail['unit_id']
    payment_duration = detail.get('duration', 'monthly')  # monthly, quarterly, yearly
    
    # Predefined pre-payment rates with discounts
    prepay_rates = {
        'monthly': {
            'rate': 100,
            'days': 30,
            'discount': 0
        },
        'quarterly': {
            'rate': 270,  # 10% off for 3 months
            'days': 90,
            'discount': 0.10
        },
        'yearly': {
            'rate': 1080,  # 20% off for 12 months
            'days': 365,
            'discount': 0.20
        }
    }
    
    # Retrieve unit details
    unit_response = unit_table.get_item(
        Key={'unit_id': unit_id}
    )
    unit = unit_response.get('Item')
    
    
    
    # Verify payment method exists
    payment_method = payments_table.get_item(
        Key={'user_id': user_id}
    ).get('Item')
    
    if not payment_method:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No payment method found"})
        }
    
    # Get payment details
    payment_config = prepay_rates.get(payment_duration, prepay_rates['monthly'])
    amount = payment_config['rate']
    
    # Calculate rental dates
    start_date = datetime.now()
    end_date = start_date + timedelta(days=payment_config['days'])
    
    # Create rental record
    rental_id = str(uuid.uuid4())
    rentals_table.put_item(
        Item={
            'rental_id': rental_id,
            'user_id': user_id,
            'unit_id': unit_id,
            'billing_option': 'pre-pay',
            'payment_duration': payment_duration,
            'monthly_rate': amount,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'discount_percentage': payment_config['discount'] * 100,
            'status': 'Active'
        }
    )
    
   
    
    # Log payment
    payments_table.put_item(
        Item={
            'payment_id': str(uuid.uuid4()),
            'user_id': user_id,
            'rental_id': rental_id,
            'amount': amount,
            'payment_type': 'pre-pay',
            'payment_method_id': payment_method['payment_id'],
            'timestamp': datetime.now().isoformat(),
            'status': 'Successful'
        }
    )
    
    logger.info(f"Pre-payment processed for user {user_id}, unit {unit_id}")
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Pre-payment successful",
            "rental_id": rental_id,
            "amount": amount,
            "duration": payment_duration,
            "discount": payment_config['discount'] * 100,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })
    }

@tracer.capture_method
def process_recurring_billing(event, context):
    """
    Process recurring billing for active rentals
    """
    logger.info("Processing recurring billing")
    
    # Scan for active rentals with recurring billing
    response = rentals_table.scan(
        FilterExpression='billing_option IN (:monthly, :yearly) AND status = :active',
        ExpressionAttributeValues={
            ':monthly': 'monthly',
            ':yearly': 'yearly',
            ':active': 'Active'
        }
    )
    
    for rental in response.get('Items', []):
        try:
            user_id = rental['user_id']
            amount = rental.get('monthly_rate', 100)  # Default rate
            
            # Log payment
            payments_table.put_item(
                Item={
                    'payment_id': str(uuid.uuid4()),
                    'user_id': user_id,
                    'rental_id': rental['rental_id'],
                    'amount': amount,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'Successful'
                }
            )
            
        except Exception as billing_error:
            logger.error(f"Billing error for rental {rental['rental_id']}: {str(billing_error)}")
            
            # Mark rental with payment issues
            rentals_table.update_item(
                Key={'rental_id': rental['rental_id']},
                UpdateExpression='SET availabilityStatus = :status',
                ExpressionAttributeValues={
                    ':status': 'Problem'
                }
            )
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Recurring billing processed"})
    }

@tracer.capture_method
def apply_rental_discount(event, context):
    """
    Apply discounts to storage unit rentals
    """
    logger.info("Applying rental discounts")
    
    detail = json.loads(event['body'])
    unit_id = detail['unit_id']
    discount_type = detail.get('discount_type', 'standard')
    
    # Define discount rates
    discount_rates = {
        'yearly': 0.15,  # 15% off for yearly rentals
        'seasonal': 0.10,  # 10% off during off-peak season
        'marketing': 0.20,  # Special marketing campaign discount
        'standard': 0.05   # Standard 5% discount
    }
    
    # Retrieve rental and unit information
    rental_response = rentals_table.get_item(
        Key={'unit_id': unit_id}
    )
    rental = rental_response.get('Item')
    
    if not rental:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Rental not found"})
        }
    
    # Calculate discounted rate
    original_rate = rental.get('monthly_rate', 100)
    discount_rate = discount_rates.get(discount_type, 0.05)
    discounted_rate = original_rate * (1 - discount_rate)
    
    # Update rental with discounted rate
    rentals_table.update_item(
        Key={'rental_id': rental['rental_id']},
        UpdateExpression='SET monthly_rate = :rate, discount_type = :discount',
        ExpressionAttributeValues={
            ':rate': discounted_rate,
            ':discount': discount_type
        }
    )
    
    logger.info(f"Applied {discount_type} discount to rental {rental['rental_id']}")
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "original_rate": original_rate,
            "discounted_rate": discounted_rate,
            "discount_percentage": discount_rate * 100
        })
    }

@tracer.capture_method
def cancel_rental(event, context):
    """
    Cancel a storage unit rental with notice period management
    """
    logger.info("Cancelling storage unit rental")
    
    detail = json.loads(event['body'])
    rental_id = detail['rental_id']
    user_id = event['requestContext']['authorizer']['claims']['sub']
    
    # Retrieve rental details
    rental_response = rentals_table.get_item(
        Key={'rental_id': rental_id}
    )
    rental = rental_response.get('Item')
    
    if not rental or rental['user_id'] != user_id:
        return {
            "statusCode": 403,
            "body": json.dumps({"error": "Unauthorized or rental not found"})
        }
    
    # Determine notice period based on rental duration
    notice_periods = {
        'monthly': timedelta(days=15),
        'yearly': timedelta(days=30),
        'indefinite': timedelta(days=7),
        'pre-pay': timedelta(days=7)
    }
    
    billing_option = rental.get('billing_option', 'monthly')
    notice_period = notice_periods.get(billing_option, timedelta(days=15))
    
    # Calculate cancellation date
    cancellation_date = datetime.now()
    effective_date = cancellation_date + notice_period
    
    # Update rental status
    rentals_table.update_item(
        Key={'rental_id': rental_id},
        UpdateExpression='SET status = :status, cancellation_date = :cancel_date, effective_date = :effective_date',
        ExpressionAttributeValues={
            ':status': 'Cancelling',
            ':cancel_date': cancellation_date.isoformat(),
            ':effective_date': effective_date.isoformat()
        }
    )
    
    # Update unit status
    unit_table.update_item(
        Key={'unit_id': rental['unit_id']},
        UpdateExpression='SET availabilityStatus = :status',
        ExpressionAttributeValues={
            ':status': 'Available'
        }
    )
    
    logger.info(f"Rental {rental_id} marked for cancellation")
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Rental cancellation initiated",
            "notice_period_days": notice_period.days,
            "effective_date": effective_date.isoformat()
        })
    }

@tracer.capture_lambda_handler
def lambda_handler(event, context):
    try:
        operation = event['httpMethod']
        path = event['path']
        
        if operation == 'POST' and '/payment-method' in path:
            return manage_payment_method(event, context)
        elif operation == 'POST' and '/discount' in path:
            return apply_rental_discount(event, context)
        # elif operation == 'POST' and '/cancel-rental' in path:
        #     return cancel_rental(event, context)
        # elif operation == 'POST' and '/process-billing' in path:
        #     return process_recurring_billing(event, context)
        # elif operation == 'POST' and '/pre-payment' in path:
        #     return process_pre_payment(event, context)
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