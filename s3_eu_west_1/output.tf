output "s3_name" {
  description = "Name of the created S3 bucket"
  value       = aws_s3_bucket.this.id
}

output "s3_location" {
  description = "Region of the created S3 bucket"
  value       = aws_s3_bucket.this.region
}
