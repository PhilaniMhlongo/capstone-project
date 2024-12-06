import json
import os
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    try:
        # Get the table name from environment variable
        table_name = os.environ.get('TABLE_NAME')
        table = dynamodb.Table(table_name)

        # Extract event details 
        detail = event.get('detail', {})
        user_id = detail.get('user_id')
        unit_id = detail.get('unit_id')
        rental_start_date = detail.get('rental_start_date', datetime.now().isoformat())
        
        # Create a unique rental ID
        rental_id = str(uuid.uuid4())

        # Prepare item for DynamoDB
        item = {
            'user_id': user_id,
            'unit_id': unit_id,
            'rental_id': rental_id,
            'rental_start_date': rental_start_date,
            'status': 'Reserved',
            'created_at': datetime.now().isoformat()
        }

        # Put item in DynamoDB
        table.put_item(Item=item)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Rental created successfully',
                'rental_id': rental_id
            })
        }

    except Exception as e:
        print(f"Error creating rental: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Failed to create rental',
                'error': str(e)
            })
        }