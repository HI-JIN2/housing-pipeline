terraform {
  backend "http" {
    # Replace with your OCI Object Storage Pre-Authenticated Request (PAR) URL
    # This URL will be overridden in GitHub Actions using -backend-config
    address        = "https://placeholder-overwrite-me"
    update_method  = "PUT"
  }
}
