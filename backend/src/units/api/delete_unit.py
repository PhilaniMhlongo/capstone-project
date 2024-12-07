import boto3
import os
import json

dynamodb = boto3.resource('dynamodb')
table_name = os.getenv('RENTAL_UNITS_TABLE')
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    try:
        # Extract the unit ID from path parameters
        unit_id = event['pathParameters']['unitId']
        
        # Delete the item
        table.delete_item(Key={'unitId': unit_id})
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Unit deleted successfully"}),
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
