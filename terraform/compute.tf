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

resource "oci_core_instance" "housing_server" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_ocid
  display_name        = "housing-pipeline-server"
  shape               = "VM.Standard.E2.1.Micro"

  # VM.Standard.E2.1.Micro does not support flex configuration (fixed 1 OCPU, 1GB RAM)

  create_vnic_details {
    subnet_id        = oci_core_subnet.housing_subnet.id
    assign_public_ip = true
    display_name     = "primaryvnic"
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

output "instance_public_ip" {
  description = "The public IP address of the provisioned server"
  value       = oci_core_instance.housing_server.public_ip
}
