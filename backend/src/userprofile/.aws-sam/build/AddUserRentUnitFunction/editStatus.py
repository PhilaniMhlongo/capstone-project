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
        new_status = detail.get('status', 'Reserved')

        # Update the rental status
        response = table.update_item(
            Key={
                'user_id': user_id,
                'unit_id': unit_id
            },
            UpdateExpression='SET #status = :new_status, updated_at = :updated_at',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':new_status': new_status,
                ':updated_at': datetime.now().isoformat()
            },
            ReturnValues='Available'
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Rental status updated successfully',
                'updated_attributes': response.get('Attributes', {})
            })
        }

    except Exception as e:
        print(f"Error updating rental status: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Failed to update rental status',
                'error': str(e)
            })
        }