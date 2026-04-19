#!/bin/bash
set -e

rm -rf package lambda_deployment.zip
mkdir -p package

pip install -r requirements.txt -t package
cp lambda_function.py package/

cd package
zip -r ../lambda_deployment.zip .
cd ..
