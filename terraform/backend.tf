terraform {
  backend "http" {
    # Replace with your OCI Object Storage Pre-Authenticated Request (PAR) URL
    # Example: https://objectstorage.ap-chuncheon-1.oraclecloud.com/p/.../b/terraform-state/o/terraform.tfstate
    address        = "INSERT_YOUR_PAR_URL_HERE"
    update_method  = "PUT"
  }
}
