# Linux Server Deployment Guide

Complete guide for deploying the VMAX Capacity Dashboard on a Linux server with Docker.

## 📋 Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+, RHEL 8+, or similar)
- **RAM**: Minimum 2GB, recommended 4GB
- **Disk**: Minimum 10GB free space
- **CPU**: 2+ cores recommended
- **Network**: Access to VMAX/PowerMax Unisphere on port 8443

### Required Software
- Docker 20.10+
- Docker Compose 2.0+
- Git
- Node.js 18+ (for frontend build)

## 🚀 Quick Deployment

### 1. Install Docker and Docker Compose

#### Ubuntu/Debian
```bash
# Update package index
sudo apt-get update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get install docker-compose-plugin

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

#### RHEL/CentOS
```bash
# Install Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Clone the Repository

```bash
cd /opt
sudo git clone https://github.com/mateim4/vMAX-Capacity-Dashboard.git
cd vMAX-Capacity-Dashboard
sudo chown -R $USER:$USER .
```

### 3. Build the Frontend

```bash
# Install Node.js if not present
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Build frontend
cd frontend
npm install
npm run build
cd ..
```

### 4. Configure the Application

```bash
# Copy example configuration
cp config.example.json config.json

# Edit configuration with your Unisphere details
nano config.json
```

**config.json example:**
```json
{
  "unisphere_host": "10.0.1.100",
  "unisphere_port": 8443,
  "username": "monitor_user",
  "password": "YourSecurePassword",
  "array_id": "000123456789",
  "verify_ssl": false
}
```

⚠️ **Security**: Protect this file!
```bash
chmod 600 config.json
```

### 5. Deploy with Docker Compose

```bash
# Start the application
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 6. Access the Dashboard

Open your browser and navigate to:
- **Dashboard**: `http://your-server-ip`
- **API Documentation**: `http://your-server-ip:8000/docs`

## 🔧 Advanced Configuration

### Using Environment Variables

Instead of `config.json`, you can use environment variables:

```bash
# Create .env file
cat > .env << 'EOF'
UNISPHERE_HOST=10.0.1.100
UNISPHERE_PORT=8443
UNISPHERE_USER=monitor_user
UNISPHERE_PASSWORD=YourSecurePassword
VMAX_ARRAY_ID=000123456789
UNISPHERE_VERIFY_SSL=false
EOF

chmod 600 .env
```

Update `docker-compose.yml` to use environment file:
```yaml
services:
  backend:
    env_file:
      - .env
```

### SSL/TLS Configuration

#### Using Let's Encrypt with Certbot

1. Install Certbot:
```bash
sudo apt-get install certbot python3-certbot-nginx
```

2. Get SSL certificate:
```bash
sudo certbot certonly --standalone -d your-domain.com
```

3. Update `nginx.conf`:
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # ... rest of configuration
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

4. Mount certificates in docker-compose.yml:
```yaml
services:
  frontend:
    volumes:
      - /etc/letsencrypt:/etc/letsencrypt:ro
```

### Persistent Data Storage

Create volumes for logs and data:

```yaml
services:
  backend:
    volumes:
      - ./config.json:/app/config.json:ro
      - ./logs:/app/logs
      - ./data:/app/data
```

### Resource Limits

Add resource constraints:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## 📊 Monitoring & Maintenance

### Health Checks

Check application health:
```bash
# Backend health
curl http://localhost:8000/api/health

# Frontend health
curl http://localhost/
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Backend only
docker compose logs -f backend

# Frontend only
docker compose logs -f frontend

# Last 100 lines
docker compose logs --tail=100
```

### Updating the Application

```bash
# Pull latest code
git pull origin main

# Rebuild frontend if changed
cd frontend
npm run build
cd ..

# Restart services
docker compose down
docker compose up -d --build
```

### Backup Configuration

```bash
# Create backup directory
mkdir -p /opt/backups/vmax-dashboard

# Backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/vmax-dashboard"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup config
cp config.json "$BACKUP_DIR/config_$DATE.json"

# Backup logs
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" logs/

# Keep only last 7 days
find "$BACKUP_DIR" -name "*.json" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x backup.sh

# Schedule daily backup
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/vMAX-Capacity-Dashboard/backup.sh") | crontab -
```

## 🔒 Security Best Practices

### 1. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw enable
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw status
```

### 2. Restrict Access by IP

Update `nginx.conf`:
```nginx
location / {
    # Allow specific IPs
    allow 10.0.0.0/8;
    allow 192.168.0.0/16;
    deny all;
    
    try_files $uri $uri/ /index.html;
}
```

### 3. Use Secrets Management

For production, use Docker secrets:

```bash
# Create secrets
echo "YourSecurePassword" | docker secret create unisphere_password -

# Update docker-compose.yml
services:
  backend:
    secrets:
      - unisphere_password
    environment:
      - UNISPHERE_PASSWORD_FILE=/run/secrets/unisphere_password

secrets:
  unisphere_password:
    external: true
```

### 4. Regular Updates

```bash
# Update Docker images
docker compose pull
docker compose up -d

# Update system packages
sudo apt-get update && sudo apt-get upgrade -y
```

## 🐛 Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs backend

# Check config file
cat config.json | python -m json.tool

# Rebuild without cache
docker compose build --no-cache
docker compose up -d
```

### Cannot Connect to Unisphere

```bash
# Test connectivity from container
docker compose exec backend sh
ping unisphere-host
nc -zv unisphere-host 8443
```

### Frontend Not Loading

```bash
# Check if frontend built successfully
ls -la frontend/build/

# Rebuild frontend
cd frontend
rm -rf build node_modules
npm install
npm run build
cd ..

# Restart containers
docker compose restart
```

### Performance Issues

```bash
# Check container resources
docker stats

# Check system resources
htop

# Increase container limits in docker-compose.yml
```

## 📈 Production Checklist

- [ ] SSL/TLS certificates configured
- [ ] Firewall rules applied
- [ ] Access restricted to authorized IPs
- [ ] Backup script configured and tested
- [ ] Monitoring alerts set up
- [ ] Resource limits configured
- [ ] Log rotation enabled
- [ ] Docker auto-restart enabled
- [ ] Documentation updated with your environment
- [ ] Disaster recovery plan documented

## 🔄 Systemd Service (Alternative)

For non-Docker deployment:

```bash
# Create systemd service
sudo cat > /etc/systemd/system/vmax-dashboard.service << 'EOF'
[Unit]
Description=VMAX Capacity Dashboard
After=network.target

[Service]
Type=simple
User=vmax
WorkingDirectory=/opt/vMAX-Capacity-Dashboard
ExecStart=/usr/local/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable vmax-dashboard
sudo systemctl start vmax-dashboard
sudo systemctl status vmax-dashboard
```

## 📞 Support

For issues:
1. Check logs: `docker compose logs -f`
2. Review configuration: `config.json`
3. Test connectivity to Unisphere
4. Check GitHub issues: https://github.com/mateim4/vMAX-Capacity-Dashboard/issues

---

**Deployment Time**: ~15-30 minutes for full setup  
**Maintenance**: Minimal - mostly log rotation and updates  
**Uptime**: 99.9% with proper configuration
