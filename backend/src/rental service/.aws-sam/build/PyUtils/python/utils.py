from boto3.dynamodb.conditions import Key
import boto3
import os

rental_table = os.getenv('TABLE_NAME')
dynamodb = boto3.resource('dynamodb')


def get_rental(facilityId,unitId):
    table = dynamodb.Table(rental_table)
    response = table.query(
        KeyConditionExpression=(Key('facilityId').eq(facilityId) & Key('unitId').eq(unitId))
    )
    
    rental=[]
    for item in response['Items']:
        rental.append(item['data'])
        
    return rental[0]