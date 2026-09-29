"""Using DynamoDb persistence infratstructure"""

from aws.dynamodb.config import DynamoDBConfig, load_dynamodb_config

__all__ = ["DynamoDBConfig", "load_dynamodb_config"]
