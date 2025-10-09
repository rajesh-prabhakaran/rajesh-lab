provider "aws" {
  region = "us-east-1"
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_exec_role" {
  name = "confluence_lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Effect = "Allow",
      Sid    = ""
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attach" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "secrets_access" {
  name        = "SecretsManagerAccess"
  description = "Allow Lambda to access Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "secretsmanager:GetSecretValue"
      ],
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "secrets_policy_attach" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.secrets_access.arn
}

# Secrets Manager
resource "aws_secretsmanager_secret" "confluence_secret" {
  name = "confluence_api_credentials"
}

resource "aws_secretsmanager_secret_version" "confluence_secret_version" {
  secret_id     = aws_secretsmanager_secret.confluence_secret.id
  secret_string = jsonencode({
    base_url = "https://your-domain.atlassian.net",
    username = "your-email@example.com",
    api_token = "your-api-token"
  })
}

# Lambda Function from parameterized S3 bucket
resource "aws_lambda_function" "confluence_lambda" {
  function_name = "confluence_page_analytics"
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.11"

  s3_bucket = var.s3_bucket_name
  s3_key    = var.s3_object_key

  environment {
    variables = {
      CONFLUENCE_SECRET_NAME = aws_secretsmanager_secret.confluence_secret.name
      CONFLUENCE_SPACE_KEY   = var.confluence_space_key  
    }
  }
}
