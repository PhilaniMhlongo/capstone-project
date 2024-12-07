import json
import os
import boto3
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    try:
        # Extract query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        status = query_params.get('status')
        page = int(query_params.get('page', 1))
        limit = int(query_params.get('limit', 10))
        
        # Prepare DynamoDB query
        table = dynamodb.Table(os.environ['STORAGE_UNITS_TABLE'])
        
        # Build filter expression if status is provided
        filter_expression = None
        if status:
            filter_expression = Attr('availabilityStatus').eq(status)
        
        # Scan or query the table
        if filter_expression:
            response = table.scan(
                FilterExpression=filter_expression,
                Limit=limit,
                # Add pagination logic if needed
            )
        else:
            response = table.scan(Limit=limit)
        
        # Prepare response
        units = response.get('Items', [])
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'units': units,
                'total': len(units),
                'page': page
            })
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }