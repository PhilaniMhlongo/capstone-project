import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Logger

# Initialize logger from AWS Lambda Powertools
logger = Logger(service="ListRentals")

dynamodb = boto3.resource('dynamodb')

@logger.inject_lambda_context
def lambda_handler(event, context):
    """
    Lambda handler to list rentals for a user
    
    Expected Event Structure:
    {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': 'user-id-from-cognito'
                }
            }
        }
    }
    """
    try:
        # Get the table name from environment variable
        table_name = os.environ['TABLE_NAME']
        table = dynamodb.Table(table_name)

        # Extract user ID from Cognito claims
        user_id = event['requestContext']['authorizer']['claims']['sub']

        # Query DynamoDB for rentals belonging to this user
        response = table.query(
            KeyConditionExpression=Key('user_id').eq(user_id)
        )

        # Extract and prepare the rental items
        rentals = response.get('Items', [])

        # Log the number of rentals found
        logger.info(f"Found {len(rentals)} rentals for user {user_id}")

        return {
            'statusCode': 200,
            'body': json.dumps(rentals),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'  # For CORS support
            }
        }

    except KeyError as e:
        logger.error(f"Missing required key in event: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid request'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }

    except Exception as e:
        logger.error(f"Error listing rentals: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }