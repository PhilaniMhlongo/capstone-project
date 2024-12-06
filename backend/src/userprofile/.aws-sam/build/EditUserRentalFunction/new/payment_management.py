import os
import json
import uuid
import boto3
from aws_lambda_powertools import Logger, Tracer
from datetime import datetime, timedelta

# Globals
logger = Logger()
tracer = Tracer(service="StorageApp")
rentals_table = os.getenv('RENTALS_TABLE')
payments_table = os.getenv('PAYMENTS_TABLE')
unit_table=os.getenv('UNIT_TABLE')
dynamodb = boto3.resource('dynamodb')
rentals_table = dynamodb.Table(rentals_table)
payments_table = dynamodb.Table(payments_table)
unit_table=dynamodb.Table(unit_table)
stripe = boto3.client('stripe')

@tracer.capture_method
def manage_payment_method(event, context):
    """
    Add or update customer payment method
    """
    logger.info("Managing payment method")
    
    detail = json.loads(event['body'])
    user_id = event['requestContext']['authorizer']['claims']['sub']
    
    payment_method_id = detail.get('payment_method_id')
    payment_type = detail.get('type', 'card')  # card or eft
    
    # Add payment method to Stripe
    stripe_customer = stripe.Customer.create(
        source=payment_method_id,
        metadata={'user_id': user_id}
    )
    
    # Store payment method in DynamoDB
    payments_table.put_item(
        Item={
            'user_id': user_id,
            'payment_method_id': stripe_customer.id,
            'type': payment_type,
            'created_at': datetime.now().isoformat()
        }
    )
    
    logger.info(f"Payment method added for user {user_id}")
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Payment method added"})
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
            
            # Retrieve payment method
            payment_method = payments_table.get_item(
                Key={'user_id': user_id}
            ).get('Item')
            
            if payment_method:
                # Charge customer via Stripe
                stripe.Charge.create(
                    amount=amount * 100,  # Amount in cents
                    currency='usd',
                    customer=payment_method['payment_method_id'],
                    description=f'Storage Unit Rental - {rental["unit_id"]}'
                )
                
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
                UpdateExpression='SET status = :status',
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
        'indefinite': timedelta(days=7)
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
        UpdateExpression='SET status = :status',
        ExpressionAttributeValues={
            ':status': 'Cancelling'
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
        elif operation == 'POST' and '/cancel-rental' in path:
            return cancel_rental(event, context)
        elif operation == 'POST' and '/process-billing' in path:
            return process_recurring_billing(event, context)
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