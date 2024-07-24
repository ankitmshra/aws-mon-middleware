import boto3
import json
from botocore.exceptions import ClientError
from django.conf import settings

def format_json(raw_json_string):
    try:
        parsed_json = json.loads(raw_json_string)
        body_json_string = parsed_json['body']
        body_json = json.loads(body_json_string)
        formatted_json = json.dumps(body_json, indent=4)
        return formatted_json
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError("Failed to format JSON") from e

def fetch_json(aws_access_key_id, aws_secret_access_key,
               aws_region, bucket_name, object_key):
    try:
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )

        s3 = session.client('s3')
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        content = response['Body'].read()
        pretty_json = format_json(content)

        return pretty_json,True

    except ValueError as e:
        return (("Error formatting JSON"), False)
    except ClientError as e:
        error_message = e.response['Error']['Message']
        return ((f"S3 ClientError: {error_message}"), False)
    except Exception as e:
        return ((f"Error fetching JSON: {str(e)}"),False)