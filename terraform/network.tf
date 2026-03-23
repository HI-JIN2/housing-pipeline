resource "oci_core_vcn" "housing_vcn" {
  cidr_block     = "10.0.0.0/16"
  compartment_id = var.compartment_ocid
  display_name   = "housing_vcn"
  dns_label      = "housingvcn"
}

resource "oci_core_internet_gateway" "housing_igw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.housing_vcn.id
  display_name   = "housing_igw"
  enabled        = true
}

resource "oci_core_default_route_table" "housing_route_table" {
  manage_default_resource_id = oci_core_vcn.housing_vcn.default_route_table_id

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.housing_igw.id
  }
}

resource "oci_core_security_list" "housing_security_list" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.housing_vcn.id
  display_name   = "housing_security_list"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    protocol = "6" # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      min = 22
      max = 22
    }
  }

  ingress_security_rules {
    protocol = "6" # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      min = 8000
      max = 8000
    }
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
    protocol = "6" # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      min = 5173
      max = 5173
    }
  }

  ingress_security_rules {
    protocol = "6" # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      min = 9090
      max = 9090
    }
  }

  ingress_security_rules {
    protocol = "6" # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      min = 3000
      max = 3000
    }
  }
}

resource "oci_core_subnet" "housing_subnet" {
  cidr_block     = "10.0.1.0/24"
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.housing_vcn.id
  display_name   = "housing_subnet"
  security_list_ids = [oci_core_security_list.housing_security_list.id]
  route_table_id = oci_core_vcn.housing_vcn.default_route_table_id
}
