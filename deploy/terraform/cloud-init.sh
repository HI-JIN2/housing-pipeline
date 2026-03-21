#!/bin/bash
# Cloud-init script to setup Docker and Compose on OCI Ubuntu
apt-get update
apt-get install -y ca-certificates cursor curl gnupg lsb-release

# Install Docker
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Setup directory
mkdir -p /home/ubuntu/housing-pipeline
chown -R ubuntu:ubuntu /home/ubuntu/housing-pipeline
