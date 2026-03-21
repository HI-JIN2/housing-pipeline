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
apt-get install -y git curl iptables-persistent

# Install Docker using the official script
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu

# Install Docker Compose V2 plugin
apt-get update
apt-get install -y docker-compose-plugin || {
  mkdir -p /usr/local/lib/docker/cli-plugins
  curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m) -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
}

# Start docker service
systemctl enable docker
systemctl start docker

# Open Ubuntu iptables for 공고zip (Ports 80, 8000, 5173)
iptables -I INPUT -p tcp -m tcp --dport 80 -j ACCEPT
iptables -I INPUT -p tcp -m tcp --dport 8000 -j ACCEPT
iptables -I INPUT -p tcp -m tcp --dport 5173 -j ACCEPT
netfilter-persistent save

# To clone and start the project automatically upon boot, uncomment and fill in:
# sudo -u ubuntu bash -c 'git clone <YOUR_REPO_URL> /home/ubuntu/housing-pipeline && cd /home/ubuntu/housing-pipeline && nohup ./start_all.sh > pipeline.log 2>&1 &'
