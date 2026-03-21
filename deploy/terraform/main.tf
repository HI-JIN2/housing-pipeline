# OCI Always Free Infrastructure Terraform
terraform {
  required_providers {
    oci = {
      source = "oracle/oci"
    }
  }
}

variable "tenancy_ocid" {}
variable "user_ocid" {}
variable "fingerprint" {}
variable "private_key_path" {}
variable "region" {}
variable "compartment_id" {}
variable "ssh_public_key" {}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

# 1. Virtual Cloud Network (VCN)
resource "oci_core_vcn" "housing_vcn" {
  compartment_id = var.compartment_id
  cidr_block     = "10.0.0.0/16"
  display_name   = "housing-vcn"
  dns_label      = "housingvcn"
}

# 2. Internet Gateway
resource "oci_core_internet_gateway" "housing_ig" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.housing_vcn.id
  display_name   = "housing-ig"
}

# 3. Route Table
resource "oci_core_route_table" "housing_rt" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.housing_vcn.id
  display_name   = "housing-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.housing_ig.id
  }
}

# 4. Security List
resource "oci_core_security_list" "housing_sl" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.housing_vcn.id
  display_name   = "housing-sl"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    protocol = "6" # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      min = 80
      max = 80
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 443
      max = 443
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 22
      max = 22
    }
  }
}

# 5. Subnet
resource "oci_core_subnet" "housing_subnet" {
  compartment_id    = var.compartment_id
  vcn_id            = oci_core_vcn.housing_vcn.id
  cidr_block        = "10.0.1.0/24"
  display_name      = "housing-subnet"
  route_table_id    = oci_core_route_table.housing_rt.id
  security_list_ids = [oci_core_security_list.housing_sl.id]
}

# 6. Compute Instance (ARM Ampere A1 - Always Free)
resource "oci_core_instance" "housing_instance" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_id
  shape               = "VM.Standard.A1.Flex"
  display_name        = "housing-pipeline-arm"

  shape_config {
    ocpus         = 4
    memory_in_gbs = 24
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu_arm.images[0].id
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.housing_subnet.id
    assign_public_ip = true
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = base64encode(file("${path.module}/cloud-init.sh"))
  }
}

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_id
}

data "oci_core_images" "ubuntu_arm" {
  compartment_id           = var.compartment_id
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

output "public_ip" {
  value = oci_core_instance.housing_instance.public_ip
}
