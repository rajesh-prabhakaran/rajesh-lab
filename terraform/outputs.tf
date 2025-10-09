output "lambda_function_name" {
  value = aws_lambda_function.confluence_lambda.function_name
}

output "secret_name" {
  value = aws_secretsmanager_secret.confluence_secret.name
}
