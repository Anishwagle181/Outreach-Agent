# Deployment Guide

This guide covers various deployment options for Outreach Agent.

## Table of Contents
1. [Docker Compose (Local)](#docker-compose-local)
2. [GitHub Actions CI/CD](#github-actions-cicd)
3. [Manual Server Deployment](#manual-server-deployment)
4. [Cloud Platforms](#cloud-platforms)

---

## Docker Compose (Local)

### Quick Start
```bash
docker-compose up -d
```

### Environment Setup
```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit with your configuration
nano backend/.env
```

### Verify Deployment
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Run health check
bash scripts/health-check.sh
```

### Access Applications
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

---

## GitHub Actions CI/CD

### Setup

#### 1. Configure Repository Secrets
Add these secrets in GitHub repo settings (Settings → Secrets and variables → Actions):

| Secret Name | Description |
|---|---|
| `DEPLOY_KEY` | SSH private key for server access |
| `DEPLOY_HOST` | Server IP or hostname |
| `DEPLOY_USER` | SSH username (e.g., ubuntu, root) |
| `GHCR_USERNAME` | GitHub username |
| `GHCR_PASSWORD` | GitHub personal access token |

#### 2. Generate SSH Deploy Key
```bash
# On your local machine
ssh-keygen -t rsa -b 4096 -f deploy_key -N ""

# Copy the private key content (deploy_key) to GitHub secret: DEPLOY_KEY
# Copy the public key to server's ~/.ssh/authorized_keys
cat deploy_key.pub
```

#### 3. Add Deploy Key to Server
```bash
# SSH into your server
ssh user@your-server.com

# Add the public key
echo "deploy_key_content_here" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Workflow Triggers

The CI/CD pipeline automatically:
- **Builds** Docker images on every push to `main` and `develop`
- **Tests** Python code with linting
- **Pushes** images to GitHub Container Registry
- **Deploys** to production on `main` branch pushes

### Manual Trigger
```bash
# Push to main to trigger deployment
git push origin main
```

### View Workflow Status
1. Go to your GitHub repository
2. Click "Actions" tab
3. Select the workflow run to see details

---

## Manual Server Deployment

### Prerequisites
- Ubuntu 20.04+ server
- Root or sudo access
- Docker & Docker Compose installed

### Installation Steps

#### 1. Install Docker
```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker-compose --version
```

#### 2. Clone Repository
```bash
cd /app
sudo git clone https://github.com/Anishwagle181/Outreach-Agent.git
cd Outreach-Agent
sudo chown -R $USER:$USER .
```

#### 3. Setup Environment
```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit with your API keys
nano backend/.env
```

Sample `.env`:
```
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./outreach.db
```

#### 4. Deploy Application
```bash
# Use provided deployment script
chmod +x scripts/deploy.sh
sudo scripts/deploy.sh

# Or manually start services
docker-compose -f docker-compose.prod.yml up -d
```

#### 5. Verify Deployment
```bash
# Check services
docker-compose ps

# Run health check
bash scripts/health-check.sh
```

### Access Application
- Frontend: http://your-server-ip:3000
- Backend: http://your-server-ip:8000

### Enable HTTPS (Let's Encrypt)

#### Option 1: Nginx + Certbot
```bash
# Install Nginx and Certbot
sudo apt install nginx certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --nginx -d yourdomain.com

# Update nginx.conf with SSL configuration
# See nginx.conf.example for reference
```

#### Option 2: Traefik (Automatic HTTPS)
```bash
# Create docker-compose.traefik.yml with Traefik configuration
# Configure automatic HTTPS with Let's Encrypt
```

---

## Cloud Platforms

### AWS Deployment (ECS)

#### Prerequisites
- AWS Account
- ECR repository created
- ECS cluster and service configured

#### Steps
```bash
# Login to AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

# Tag and push images
docker tag outreach-agent-backend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/outreach-backend:latest
docker tag outreach-agent-frontend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/outreach-frontend:latest

docker push <account>.dkr.ecr.us-east-1.amazonaws.com/outreach-backend:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/outreach-frontend:latest

# Update ECS service task definition with new image URIs
```

### Heroku Deployment

```bash
# Install Heroku CLI
npm install -g heroku

# Login to Heroku
heroku login

# Create app
heroku create outreach-agent

# Add buildpack for Python
heroku buildpacks:add heroku/python

# Set environment variables
heroku config:set GROQ_API_KEY=your_key
heroku config:set SECRET_KEY=your_secret

# Deploy
git push heroku main
```

### Railway.app Deployment

1. Connect GitHub repository
2. Create services for frontend and backend
3. Set environment variables
4. Deploy automatically

### Render.com Deployment

1. Create new web services
2. Connect Docker Compose
3. Set environment variables
4. Deploy

---

## Monitoring & Maintenance

### Monitor Logs
```bash
# View recent logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f backend

# Export logs
docker-compose logs > logs.txt
```

### Database Backup
```bash
# Backup SQLite database
cp backend/outreach.db backups/outreach.db.backup.$(date +%Y%m%d_%H%M%S)

# Backup with Docker
docker-compose exec backend cp /app/outreach.db /backups/outreach.db
```

### Update Application
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### Health Monitoring
```bash
# Check service health
docker-compose ps

# Monitor resource usage
docker stats

# Check logs for errors
docker-compose logs --grep "ERROR"
```

---

## Troubleshooting

### Services Won't Start
```bash
# Check logs for errors
docker-compose logs

# Verify environment variables
docker-compose config

# Restart services
docker-compose restart

# Full reset
docker-compose down -v
docker-compose up -d
```

### Port Already in Use
```bash
# Find process using port
lsof -i :3000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Database Locked
```bash
# This often happens with SQLite
# Solution 1: Use PostgreSQL in production
# Solution 2: Restart backend service
docker-compose restart backend
```

### Out of Disk Space
```bash
# Clean up unused Docker resources
docker system prune -a

# Remove old containers
docker-compose down -v
```

---

## Security Checklist

- [ ] Change default SECRET_KEY
- [ ] Keep GROQ_API_KEY secure (use .env)
- [ ] Enable HTTPS/SSL
- [ ] Regularly update Docker images
- [ ] Set up firewall rules
- [ ] Backup database regularly
- [ ] Monitor logs for suspicious activity
- [ ] Use strong passwords for authentication
- [ ] Consider database encryption
- [ ] Implement rate limiting

---

## Performance Optimization

### For Production
```bash
# Use PostgreSQL instead of SQLite
# Database URL: postgresql://user:pass@host/dbname

# Enable caching
# Use Redis for session management

# Implement CDN for frontend
# Use Nginx reverse proxy for load balancing

# Monitor with: New Relic, DataDog, etc.
```

### Docker Optimization
```bash
# Reduce image size
# Use alpine Linux images
# Multi-stage builds
# Minimize layers
```

---

## Support

- **Issues**: https://github.com/Anishwagle181/Outreach-Agent/issues
- **Documentation**: README.md
- **Quick Start**: QUICKSTART.md

---

**Last Updated**: 2026-06-05
