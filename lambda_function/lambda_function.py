import json
import boto3
import urllib.request
import os

s3 = boto3.client('s3')

BACKEND_API_URL = os.environ.get("BACKEND_API_URL")
BACKEND_API_KEY = os.environ.get("BACKEND_API_KEY")

def lambda_handler(event, context):
    results = []

    try:
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']

            print(f"Processing file: {key}")

            # Read file from S3
            response = s3.get_object(Bucket=bucket, Key=key)
            prompt = response['Body'].read().decode('utf-8')

            print("Calling backend API...")

            # Prepare request
            data = json.dumps({"prompt": prompt}).encode("utf-8")

            req = urllib.request.Request(
                BACKEND_API_URL,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": BACKEND_API_KEY
                },
                method="POST"
            )

            # Call backend
            with urllib.request.urlopen(req) as res:
                response_data = json.loads(res.read().decode("utf-8"))

            result = response_data.get("response", "No response from backend")

            # Define output path
            output_key = key.replace("input/", "outputs/").replace(".txt", "_response.txt")

            print(f"Writing output to: {output_key}")

            # Write to S3
            s3.put_object(
                Bucket=bucket,
                Key=output_key,
                Body=result.encode('utf-8')
            )

            results.append({
                "input_key": key,
                "output_key": output_key,
                "status": "success"
            })

        return {
            "statusCode": 200,
            "body": json.dumps(results)
        }

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "error",
                "error": str(e)
            })
        }