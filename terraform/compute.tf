data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_ocid
}

data "oci_core_images" "ubuntu_amd" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = "VM.Standard.E2.1.Micro"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

data "oci_core_images" "ubuntu_arm" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# 1. Existing AMD Instance (Safety)
resource "oci_core_instance" "housing_server" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_ocid
  display_name        = "housing-pipeline-server-amd"
  shape               = "VM.Standard.E2.1.Micro"

  create_vnic_details {
    subnet_id        = oci_core_subnet.housing_subnet.id
    assign_public_ip = true
    display_name     = "primaryvnic-amd"
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu_amd.images[0].id
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = base64encode(file("${path.module}/userdata.sh"))
  }
}

# 2. New ARM Instance (Goal)
resource "oci_core_instance" "housing_server_arm" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_ocid
  display_name        = "housing-pipeline-server-arm"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = 4
    memory_in_gbs = 24
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.housing_subnet.id
    assign_public_ip = true
    display_name     = "primaryvnic-arm"
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu_arm.images[0].id
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = base64encode(file("${path.module}/userdata.sh"))
  }
}

output "amd_instance_public_ip" {
  description = "The public IP address of the AMD server"
  value       = oci_core_instance.housing_server.public_ip
}

output "arm_instance_public_ip" {
  description = "The public IP address of the ARM server"
  value       = oci_core_instance.housing_server_arm.public_ip
}
