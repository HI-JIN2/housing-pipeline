variable "tenancy_ocid" {
  description = "The Tenancy OCID"
  type        = string
}

variable "user_ocid" {
  description = "The User OCID"
  type        = string
}

variable "fingerprint" {
  description = "API Key Fingerprint"
  type        = string
}

variable "private_key_path" {
  description = "Path to API Private Key"
  type        = string
}

variable "region" {
  description = "Oracle Region (e.g., ap-seoul-1)"
  type        = string
  default     = "ap-seoul-1"
}

variable "compartment_ocid" {
  description = "The Compartment OCID where resources will be created"
  type        = string
}

variable "ssh_public_key" {
  description = "Public SSH key for Ubuntu login"
  type        = string
}
