import json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
from aws_lambda_powertools import Logger, Tracer

# Globals
logger = Logger()
tracer = Tracer(service="StorageApp")
storage_units_table = os.getenv('STORAGE_UNITS_TABLE')
facilities_table = os.getenv('FACILITIES_TABLE')
dynamodb = boto3.resource('dynamodb')
units_table = dynamodb.Table(storage_units_table)
facilities_table = dynamodb.Table(facilities_table)

@tracer.capture_method 
def list_storage_units(event, context):
    """
    List available storage units based on various filters
    """
    logger.info("Listing storage units")
    
    # Optional query parameters
    facility_id = event.get('queryStringParameters', {}).get('facilityId')
    min_size = event.get('queryStringParameters', {}).get('minSize')
    max_size = event.get('queryStringParameters', {}).get('maxSize')
    status = event.get('queryStringParameters', {}).get('status', 'Available')

    # Construct query conditions
    query_conditions = Key('status').eq(status)
    
    if facility_id:
        query_conditions &= Key('facility_id').eq(facility_id)
    
    response = units_table.scan(
        FilterExpression=query_conditions
    )
    
    units = response.get('Items', [])
    
    # Optional size filtering
    if min_size:
        units = [unit for unit in units if unit['size_sq_ft'] >= float(min_size)]
    if max_size:
        units = [unit for unit in units if unit['size_sq_ft'] <= float(max_size)]
    
    logger.info(f"Found {len(units)} storage units matching criteria")
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "units": units
        })
    }

@tracer.capture_lambda_handler
def lambda_handler(event, context):
    try:
        return list_storage_units(event, context)
    except Exception as err:
        logger.exception(err)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(err)})
        }