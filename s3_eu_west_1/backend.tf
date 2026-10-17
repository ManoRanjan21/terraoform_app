terraform {
  backend "s3" {
    bucket  = "dbx-backend-tf"
    region  = "us-east-1"
    profile = "dbx-test-user"
  }
}
