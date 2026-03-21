#!/bin/bash
export DEBIAN_FRONTEND=noninteractive

# Update system and install essential packages
apt-get update -y
apt-get install -y docker.io docker-compose git curl iptables-persistent

# Start docker service and grant permissions to ubuntu user
systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu

# Open Ubuntu iptables for 공고zip UI (Port 8000)
iptables -I INPUT -p tcp -m tcp --dport 8000 -j ACCEPT
netfilter-persistent save

# To clone and start the project automatically upon boot, uncomment and fill in:
# sudo -u ubuntu bash -c 'git clone <YOUR_REPO_URL> /home/ubuntu/housing-pipeline && cd /home/ubuntu/housing-pipeline && nohup ./start_all.sh > pipeline.log 2>&1 &'
