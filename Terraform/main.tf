terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"  # Update to the latest version
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.1.0"  # Update to the latest version
    }
  }
  required_version = ">= 1.0.0"  # Ensure you have a recent version of Terraform
}
provider "aws" {
  region = "us-east-1"  # Change to your preferred region
}
# Add the random provider
provider "random" {
  # No additional configuration is needed
}
# Create an S3 bucket for storing the JSON output
resource "aws_s3_bucket" "output_bucket" {
  bucket = "unused-resources-output"
#  acl    = "private"
}

resource "aws_s3_bucket_versioning" "versioning_example" {
  bucket = aws_s3_bucket.output_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}


# Create an IAM role for your Python script
resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_exec_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}
# Attach policies to the IAM role
resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSLambdaExecute"
}
resource "aws_iam_role_policy_attachment" "view_policy_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

# Create a Lambda function
resource "aws_lambda_function" "unused_resources_checker" {
  filename         = "function.zip"  # Path to your Lambda deployment package
  function_name    = "unused_resources_checker"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = filebase64sha256("function.zip")
  timeout = 300
  tags = {
    Environment = "Demo-Hackathon24"
  }
  environment {
    variables = {
      REGION = "us-east-1"  # Change to your preferred region
    }
  }
}
# Create a random ID for unique statement ID
resource "random_id" "unique" {
  byte_length = 8
}
# Allow CloudWatch to log Lambda function results
resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch-${random_id.unique.hex}-1"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.unused_resources_checker.function_name
  principal     = "events.amazonaws.com"
}
# Schedule Lambda function with CloudWatch Events
resource "aws_cloudwatch_event_rule" "every_5_minutes" {
  name                = "run_every_5_minutes"
  schedule_expression = "rate(5 minutes)"
}
resource "aws_cloudwatch_event_target" "target_lambda" {
  rule      = aws_cloudwatch_event_rule.every_5_minutes.name
  target_id = "lambda"
  arn       = aws_lambda_function.unused_resources_checker.arn
}
resource "aws_lambda_permission" "allow_cloudwatch_to_invoke" {
  statement_id  = "AllowExecutionFromCloudWatch-${random_id.unique.hex}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.unused_resources_checker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every_5_minutes.arn
}

