import boto3
import json
import uuid
import os

dynamodb = boto3.resource('dynamodb')
table_name = os.getenv('RENTAL_UNITS_TABLE')
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    try:
        # Parse the request body
        body = json.loads(event['body'])
        
        # Generate a unique ID for the unit
        unit_id = str(uuid.uuid4())
        
        # Construct the item
        item = {
            "unitId": unit_id,
            "imageUrl": body['imageUrl'],
            "name": body['name'],
            "size": body['size'],
            "location": body['location']
        }
        
        # Save to DynamoDB
        table.put_item(Item=item)
        
        return {
            "statusCode": 201,
            "body": json.dumps({"message": "Unit added successfully", "unitId": unit_id}),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        }
