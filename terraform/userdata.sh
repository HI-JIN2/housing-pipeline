#!/bin/bash
export DEBIAN_FRONTEND=noninteractive

# Create 2GB Swap file for stability on 1GB RAM
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# Update system and install essential packages
apt-get update -y
apt-get install -y docker.io docker-compose-plugin git curl iptables-persistent

# Start docker service and grant permissions to ubuntu user
systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu

# Open Ubuntu iptables for 공고zip (Ports 80, 8000, 5173)
iptables -I INPUT -p tcp -m tcp --dport 80 -j ACCEPT
iptables -I INPUT -p tcp -m tcp --dport 8000 -j ACCEPT
iptables -I INPUT -p tcp -m tcp --dport 5173 -j ACCEPT
netfilter-persistent save

# To clone and start the project automatically upon boot, uncomment and fill in:
# sudo -u ubuntu bash -c 'git clone <YOUR_REPO_URL> /home/ubuntu/housing-pipeline && cd /home/ubuntu/housing-pipeline && nohup ./start_all.sh > pipeline.log 2>&1 &'
