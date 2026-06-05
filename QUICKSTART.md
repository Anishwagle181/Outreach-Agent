# Quick Start Guide - Outreach Agent

## Option 1: Local Development (Without Docker)

### Setup
```bash
# Clone repository
git clone https://github.com/Anishwagle181/Outreach-Agent.git
cd Outreach-Agent

# Setup backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your Groq API key
```

### Run
```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
python -m http.server 3000
```

Visit: `http://localhost:3000`

---

## Option 2: Docker Compose (Recommended)

### Prerequisites
- Docker Desktop (or Docker + Docker Compose)
- Groq API key

### Setup
```bash
# Clone repository
git clone https://github.com/Anishwagle181/Outreach-Agent.git
cd Outreach-Agent

# Copy environment file
cp backend/.env.example backend/.env
# Edit backend/.env with your Groq API key
```

### Run
```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Visit: `http://localhost:3000`

---

## Option 3: Production Deployment

### Prerequisites
- Linux server (Ubuntu 20.04+)
- Docker & Docker Compose installed
- SSH access

### Setup on Server
```bash
# On your server
mkdir -p /app/outreach-agent
cd /app/outreach-agent

# Clone repository
git clone https://github.com/Anishwagle181/Outreach-Agent.git .

# Copy environment file
cp backend/.env.example backend/.env
# Edit with your API keys
```

### Deployment
```bash
# Make deploy script executable
chmod +x scripts/deploy.sh

# Run deployment
sudo scripts/deploy.sh
```

---

## Common Commands

### Docker Compose Commands
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [backend|frontend]

# Restart a service
docker-compose restart backend

# Remove volumes (clean slate)
docker-compose down -v
```

### Health Check
```bash
# Check service health
bash scripts/health-check.sh

# Or manually
curl http://localhost:8000/docs
curl http://localhost:3000
```

### Troubleshooting
```bash
# View all logs
docker-compose logs

# Check specific service
docker-compose logs backend

# Rebuild images
docker-compose build --no-cache

# Prune unused Docker resources
docker system prune -a
```

---

## Configuration

### Backend Environment Variables (.env)
```
GROQ_API_KEY=                           # Your Groq API key
SECRET_KEY=                             # Generate: openssl rand -hex 32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./outreach.db
```

### Generate Secure Secret Key
```bash
openssl rand -hex 32
# Copy the output to SECRET_KEY in .env
```

---

## API Documentation

### Access API Docs
Navigate to: `http://localhost:8000/docs`

### Key Endpoints
- **POST** `/auth/signup` - Create account
- **POST** `/auth/login` - Login
- **GET** `/people/` - List contacts
- **POST** `/people/` - Create contact
- **POST** `/ai/handle-reply` - Generate reply
- **POST** `/ai/refine-reply` - Refine reply with feedback

---

## First Steps After Starting

1. **Create Account** - Go to `http://localhost:3000` and sign up
2. **Add Contact** - Create a new lead/contact
3. **Generate Reply** - Paste a prospect message and let AI respond
4. **Refine Reply** - Use feedback button to improve the response
5. **Schedule Call** - Link your Calendly to close deals

---

## Support & Issues

- **GitHub Issues**: https://github.com/Anishwagle181/Outreach-Agent/issues
- **Documentation**: See README.md
- **API Docs**: http://localhost:8000/docs (when running)

---

## Next Steps

1. Customize system prompts in `backend/routers/ai_router.py`
2. Add email/Slack integration
3. Deploy to production
4. Set up monitoring and alerting

**Happy prospecting! 🚀**
