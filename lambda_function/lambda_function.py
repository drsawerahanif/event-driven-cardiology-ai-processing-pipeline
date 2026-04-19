import json
import os
import urllib.parse

import boto3
import requests

s3 = boto3.client("s3")

BACKEND_API_URL = os.environ["BACKEND_API_URL"]
BACKEND_API_KEY = os.environ.get("BACKEND_API_KEY")
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET")


def lambda_handler(event, context):
    results = []

    for record in event.get("Records", []):
        bucket_name = record["s3"]["bucket"]["name"]
        object_key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

        if not object_key.endswith(".txt"):
            results.append({
                "key": object_key,
                "status": "skipped",
                "reason": "Not a .txt file"
            })
            continue

        try:
            s3_response = s3.get_object(Bucket=bucket_name, Key=object_key)
            prompt_text = s3_response["Body"].read().decode("utf-8").strip()

            headers = {"Content-Type": "application/json"}
            if BACKEND_API_KEY:
                headers["x-api-key"] = BACKEND_API_KEY

            api_response = requests.post(
                BACKEND_API_URL,
                json={"prompt": prompt_text},
                headers=headers,
                timeout=30
            )
            api_response.raise_for_status()
            response_data = api_response.json()

            ai_response = response_data.get("response", "")

            base_name = object_key.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            output_key = f"outputs/{base_name}_response.txt"

            target_bucket = OUTPUT_BUCKET or bucket_name

            s3.put_object(
                Bucket=target_bucket,
                Key=output_key,
                Body=ai_response.encode("utf-8"),
                ContentType="text/plain"
            )

            results.append({
                "input_key": object_key,
                "output_key": output_key,
                "status": "success"
            })

        except Exception as e:
            results.append({
                "key": object_key,
                "status": "error",
                "error": str(e)
            })

    return {
        "statusCode": 200,
        "body": json.dumps(results)
    }
