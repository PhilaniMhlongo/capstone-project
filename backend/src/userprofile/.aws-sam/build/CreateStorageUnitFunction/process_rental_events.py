import json
import os
import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import SQSEvent

# Initialize AWS clients and utilities
logger = Logger(service=os.getenv('POWERTOOLS_SERVICE_NAME', 'rental-event-processor'))
dynamodb = boto3.resource('dynamodb')
eventbridge = boto3.client('events')

# Configuration constants
RENTALS_TABLE_NAME = os.getenv('RENTALS_TABLE')
UNIT_BUS_NAME = os.getenv('UNIT_BUS')

class RentalEventProcessor:
    @staticmethod
    def process_rental_booking(event_detail: dict):
        """
        Process a rental booking event with robust error handling and idempotency
        
        Args:
            event_detail (dict): Detailed event information for rental booking
        
        Returns:
            dict: Processing result
        """
        try:
            # Validate required fields
            required_fields = ['unit_id', 'user_id', 'booking_date']
            for field in required_fields:
                if field not in event_detail:
                    raise ValueError(f"Missing required field: {field}")
            
            # Prepare rental record
            rental_record = {
                'rental_id': f"rental-{event_detail['unit_id']}-{event_detail['user_id']}",
                'unit_id': event_detail['unit_id'],
                'user_id': event_detail['user_id'],
                'booking_date': event_detail['booking_date'],
                'Rentalstatus': 'PENDING'
            }
            
            # Store in DynamoDB
            rentals_table = dynamodb.Table(RENTALS_TABLE_NAME)
            rentals_table.put_item(Item=rental_record)
            
            # Publish confirmation event
            eventbridge.put_events(
                Entries=[
                    {
                        'Source': 'rental-service',
                        'DetailType': 'rental.booking.confirmed',
                        'EventBusName': UNIT_BUS_NAME,
                        'Detail': json.dumps({
                            'rental_id': rental_record['rental_id'],
                            'status': 'CONFIRMED'
                        })
                    }
                ]
            )
            
            logger.info(f"Processed rental booking: {rental_record['rental_id']}")
            return {"status": "success", "rental_id": rental_record['rental_id']}
        
        except Exception as e:
            logger.error(f"Error processing rental booking: {str(e)}")
            # Publish failure event
            eventbridge.put_events(
                Entries=[
                    {
                        'Source': 'rental-service',
                        'DetailType': 'rental.booking.failed',
                        'EventBusName': UNIT_BUS_NAME,
                        'Detail': json.dumps({
                            'error': str(e),
                            'original_event': event_detail
                        })
                    }
                ]
            )
            raise

def lambda_handler(event: SQSEvent, context: LambdaContext):
    """
    Lambda handler for processing SQS messages for rental events
    
    Args:
        event (SQSEvent): SQS event containing rental processing messages
        context (LambdaContext): Lambda context object
    
    Returns:
        dict: Processing results
    """
    logger.info(f"Received {len(event.records)} SQS messages")
    
    results = []
    for record in event.records:
        try:
            # Parse the message
            message_body = json.loads(record.body)
            
            # Extract event details (assuming a specific event structure)
            event_detail = message_body.get('detail', {})
            event_type = message_body.get('detail-type')
            
            # Route to appropriate processor based on event type
            if event_type == 'rental.booking.requested':
                result = RentalEventProcessor.process_rental_booking(event_detail)
                results.append(result)
            else:
                logger.warning(f"Unhandled event type: {event_type}")
        
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}")
            # Implement dead-letter queue or specific error handling
            results.append({"status": "failed", "error": str(e)})
    
    return {
        "batchItemFailures": [
            {"itemIdentifier": record.message_id} 
            for record in event.records 
            if record.body not in results
        ]
    }