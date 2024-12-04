import json
import os
import boto3
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

        # Cancel the rental by updating its status
        response = table.update_item(
            Key={
                'user_id': user_id,
                'unit_id': unit_id
            },
            UpdateExpression='SET #status = :canceled_status, canceled_at = :canceled_at',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':canceled_status': 'CANCELED',
                ':canceled_at': datetime.now().isoformat()
            },
            ReturnValues='UPDATED_NEW'
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Rental canceled successfully',
                'updated_attributes': response.get('Attributes', {})
            })
        }

    except Exception as e:
        print(f"Error canceling rental: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Failed to cancel rental',
                'error': str(e)
            })
        }