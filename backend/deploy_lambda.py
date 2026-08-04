"""
Deploy LogiSight backend to AWS Lambda + API Gateway.
Uses a container image pushed to ECR.

Prerequisites:
  - AWS CLI configured (aws configure)
  - Docker installed and running

Usage:
  python deploy_lambda.py
"""

import json
import os
import subprocess
import sys
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
REGION = "us-east-1"
ACCOUNT_ID = "401528908264"
FUNCTION_NAME = "logisight-api"
ECR_REPO = "logisight-api"
IMAGE_TAG = "latest"
MEMORY_SIZE = 512  # MB
TIMEOUT = 60  # seconds
API_NAME = "logisight-api"

ECR_URI = f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/{ECR_REPO}"
IMAGE_URI = f"{ECR_URI}:{IMAGE_TAG}"

# Environment variables for the Lambda function
LAMBDA_ENV_VARS = {
    "COCKROACHDB_URL": os.environ.get("COCKROACHDB_URL", ""),
    "COGNITO_USER_POOL_ID": os.environ.get("COGNITO_USER_POOL_ID", ""),
    "COGNITO_CLIENT_ID": os.environ.get("COGNITO_CLIENT_ID", ""),
    "COGNITO_REGION": os.environ.get("COGNITO_REGION", REGION),
    "GROQ_API_KEY": os.environ.get("GROQ_API_KEY", ""),
    "GROQ_MODEL_ID": os.environ.get("GROQ_MODEL_ID", "llama-3.3-70b-versatile"),
    "S3_INVOICE_BUCKET": os.environ.get("S3_INVOICE_BUCKET", "logisight-invoices-hackathon"),
    "AWS_REGION_NAME": REGION,
    "CORS_ORIGINS": os.environ.get("CORS_ORIGINS", "https://logi-sight.vercel.app,http://localhost:5173"),
}


def run(cmd, check=True, capture=False):
    """Run a shell command."""
    print(f"  -> {cmd}")
    result = subprocess.run(cmd, shell=True, check=check,
                            capture_output=capture, text=True)
    if capture:
        return result.stdout.strip()
    return result


def step(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def main():
    # ── Step 1: Create ECR repository (if not exists) ──────────────────────
    step("1/6 - Creating ECR repository")
    try:
        run(f'aws ecr create-repository --repository-name {ECR_REPO} '
            f'--region {REGION} --image-scanning-configuration scanOnPush=true',
            capture=True)
        print("  OK ECR repository created")
    except subprocess.CalledProcessError:
        print("  OK ECR repository already exists")

    # ── Step 2: Login to ECR ───────────────────────────────────────────────
    step("2/6 - Logging in to ECR")
    run(f'aws ecr get-login-password --region {REGION} | '
        f'docker login --username AWS --password-stdin {ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com')

    # ── Step 3: Build & push Docker image ──────────────────────────────────
    step("3/6 - Building Docker image")
    run(f'docker build -t {ECR_REPO}:{IMAGE_TAG} .')
    run(f'docker tag {ECR_REPO}:{IMAGE_TAG} {IMAGE_URI}')

    step("4/6 - Pushing image to ECR")
    run(f'docker push {IMAGE_URI}')

    # ── Step 4: Create/Update Lambda function ──────────────────────────────
    step("5/6 - Deploying Lambda function")
    env_json = json.dumps({"Variables": LAMBDA_ENV_VARS})
    with open("env_vars.json", "w") as f:
        f.write(env_json)

    # Check if function exists
    try:
        run(f'aws lambda get-function --function-name {FUNCTION_NAME} --region {REGION}',
            capture=True)
        # Update existing
        print("  Updating existing function...")
        run(f'aws lambda update-function-code '
            f'--function-name {FUNCTION_NAME} '
            f'--image-uri {IMAGE_URI} '
            f'--region {REGION}',
            capture=True)
        time.sleep(5)  # Wait for update to propagate
        run(f"aws lambda update-function-configuration "
            f"--function-name {FUNCTION_NAME} "
            f"--memory-size {MEMORY_SIZE} "
            f"--timeout {TIMEOUT} "
            f"--environment file://env_vars.json "
            f"--region {REGION}",
            capture=True)
    except subprocess.CalledProcessError:
        # Create new function
        print("  Creating new function...")
        # First, create the execution role
        role_arn = create_lambda_role()
        time.sleep(10)  # Wait for IAM role propagation

        run(f"aws lambda create-function "
            f"--function-name {FUNCTION_NAME} "
            f"--package-type Image "
            f"--code ImageUri={IMAGE_URI} "
            f"--role {role_arn} "
            f"--memory-size {MEMORY_SIZE} "
            f"--timeout {TIMEOUT} "
            f"--environment file://env_vars.json "
            f"--region {REGION}",
            capture=True)

    print("  OK Lambda function deployed")

    # ── Step 5: Create API Gateway ─────────────────────────────────────────
    step("6/6 - Setting up API Gateway")
    api_url = setup_api_gateway()

    # ── Done ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  OK DEPLOYMENT COMPLETE!")
    print(f"{'='*60}")
    print(f"  Backend URL: {api_url}")
    print(f"\n  Next steps:")
    print(f"  1. Set VITE_API_URL={api_url} in Vercel environment variables")
    print(f"  2. Redeploy the Vercel frontend")
    print(f"{'='*60}\n")


def create_lambda_role():
    """Create IAM execution role for Lambda."""
    role_name = f"{FUNCTION_NAME}-role"
    trust_policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    })

    try:
        with open("trust_policy.json", "w") as f:
            f.write(trust_policy)
        result = run(
            f"aws iam create-role --role-name {role_name} "
            f"--assume-role-policy-document file://trust_policy.json "
            f"--region {REGION}",
            capture=True
        )
        role_arn = json.loads(result)["Role"]["Arn"]

        # Attach basic Lambda execution policy
        run(f"aws iam attach-role-policy --role-name {role_name} "
            f"--policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")

        # Attach S3 read access
        run(f"aws iam attach-role-policy --role-name {role_name} "
            f"--policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess")

        # Attach Cognito access
        run(f"aws iam attach-role-policy --role-name {role_name} "
            f"--policy-arn arn:aws:iam::aws:policy/AmazonCognitoPowerUser")

        return role_arn
    except subprocess.CalledProcessError:
        # Role already exists
        result = run(f"aws iam get-role --role-name {role_name}", capture=True)
        return json.loads(result)["Role"]["Arn"]


def setup_api_gateway():
    """Create HTTP API Gateway with Lambda integration."""
    # Check if API already exists
    apis_json = run(
        f"aws apigatewayv2 get-apis --region {REGION}", capture=True
    )
    apis = json.loads(apis_json).get("Items", [])
    existing = [a for a in apis if a["Name"] == API_NAME]

    if existing:
        api_id = existing[0]["ApiId"]
        print(f"  OK API Gateway already exists: {api_id}")
    else:
        # Create HTTP API with Lambda integration
        lambda_arn = run(
            f"aws lambda get-function --function-name {FUNCTION_NAME} "
            f"--region {REGION} --query Configuration.FunctionArn --output text",
            capture=True
        )

        result = run(
            f'aws apigatewayv2 create-api '
            f'--name {API_NAME} '
            f'--protocol-type HTTP '
            f'--target {lambda_arn} '
            f'--region {REGION}',
            capture=True
        )
        api_id = json.loads(result)["ApiId"]

        # Grant API Gateway permission to invoke Lambda
        run(f'aws lambda add-permission '
            f'--function-name {FUNCTION_NAME} '
            f'--statement-id apigateway-invoke '
            f'--action lambda:InvokeFunction '
            f'--principal apigateway.amazonaws.com '
            f'--source-arn "arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}/*" '
            f'--region {REGION}',
            capture=True)

        print(f"  OK API Gateway created: {api_id}")

    api_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com"
    return api_url


if __name__ == "__main__":
    main()
