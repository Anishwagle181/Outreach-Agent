# Outreach Agent - Nexa Lead

AI-powered LinkedIn CRM with Charlie Morgan-style sales decision engine for intelligent objection handling and lead qualification.

## Features

- 🤖 **AI-Powered Replies** - Groq-powered response generation with Charlie Morgan sales framework
- 🔄 **Iterative Refinement** - Feedback loop for continuous reply improvement
- 💬 **Conversation Management** - Full conversation history with database persistence
- 🔐 **Authentication** - JWT-based user authentication
- 📊 **Sales Decision Engine** - Intelligent lead classification (Closed → Soft Objection → Curious → Interested → Ready)
- 🎯 **Intent Classification** - AI-driven intent detection for better follow-ups

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Uvicorn
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Database**: SQLite (development) / PostgreSQL (production)
- **AI**: Groq API (llama-3.3-70b-versatile)
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions

## Local Development

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized development)
- Groq API key (get from https://console.groq.com)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Anishwagle181/Outreach-Agent.git
   cd Outreach-Agent
   ```

2. **Set up environment variables**
   ```bash
   cp backend/.env.example backend/.env
   ```
   
   Edit `backend/.env` and add your Groq API key:
   ```
   GROQ_API_KEY=your_api_key_here
   SECRET_KEY=your_secret_key_here
   ```

3. **Install dependencies** (without Docker)
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Run locally**
   ```bash
   # Terminal 1 - Backend
   cd backend
   python -m uvicorn main:app --host 0.0.0.0 --port 8000

   # Terminal 2 - Frontend
   cd frontend
   python -m http.server 3000
   ```

   Visit `http://localhost:3000` in your browser.

## Docker Deployment

### Build and Run with Docker Compose

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Build Individual Images

**Backend:**
```bash
docker build -f Dockerfile.backend -t outreach-agent-backend:latest .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key -e SECRET_KEY=your_key outreach-agent-backend:latest
```

**Frontend:**
```bash
docker build -f Dockerfile.frontend -t outreach-agent-frontend:latest .
docker run -p 3000:3000 outreach-agent-frontend:latest
```

## Production Deployment

### GitHub Actions CI/CD Pipeline

The repository includes automated CI/CD using GitHub Actions that:

1. **Builds** Docker images for backend and frontend
2. **Pushes** to GitHub Container Registry (ghcr.io)
3. **Tests** Python code with linting
4. **Deploys** to production server (requires configuration)

#### Setup GitHub Secrets for Deployment

In your GitHub repository settings, add these secrets:

- `DEPLOY_KEY` - SSH private key for server access
- `DEPLOY_HOST` - Server hostname/IP
- `DEPLOY_USER` - SSH username

#### Enable Deployment

Uncomment and configure the `deploy` job in `.github/workflows/deploy.yml` for your infrastructure.

### Manual Docker Hub Deployment

```bash
# Login to Docker
docker login

# Tag images
docker tag outreach-agent-backend:latest yourusername/outreach-agent-backend:latest
docker tag outreach-agent-frontend:latest yourusername/outreach-agent-frontend:latest

# Push to Docker Hub
docker push yourusername/outreach-agent-backend:latest
docker push yourusername/outreach-agent-frontend:latest
```

Pull and run on your server:
```bash
docker pull yourusername/outreach-agent-backend:latest
docker pull yourusername/outreach-agent-frontend:latest
docker-compose up -d
```

## API Endpoints

### Authentication
- `POST /auth/signup` - Create new account
- `POST /auth/login` - Login and get JWT token

### People Management
- `GET /people/` - List all contacts
- `POST /people/` - Create new contact
- `GET /people/{person_id}` - Get contact details
- `PUT /people/{person_id}` - Update contact
- `DELETE /people/{person_id}` - Delete contact

### AI Features
- `POST /ai/handle-reply` - Analyze prospect reply and generate response
- `POST /ai/refine-reply` - Refine reply based on feedback
- `POST /ai/analyze-calendar` - Extract calendar availability

### Settings
- `GET /settings/` - Get user settings
- `PUT /settings/` - Update user settings

See `/docs` endpoint for full Swagger documentation.

## Project Structure

```
.
├── backend/
│   ├── auth.py                 # Authentication logic
│   ├── database.py             # Database configuration
│   ├── main.py                 # FastAPI app factory
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   ├── routers/
│   │   ├── auth_router.py      # Auth endpoints
│   │   ├── people_router.py    # People/contact endpoints
│   │   ├── ai_router.py        # AI/reply endpoints
│   │   └── settings_router.py  # Settings endpoints
│   └── requirements.txt         # Python dependencies
├── frontend/
│   └── index.html              # Single-page application
├── conversations/              # Sample conversations
├── Dockerfile.backend          # Backend container config
├── Dockerfile.frontend         # Frontend container config
├── docker-compose.yml          # Orchestration config
├── .github/workflows/          # CI/CD pipelines
└── README.md                   # This file
```

## Environment Variables

**Backend (.env):**
```
GROQ_API_KEY=                   # Your Groq API key
SECRET_KEY=                     # JWT secret key (generate with: openssl rand -hex 32)
ALGORITHM=HS256                 # JWT algorithm
ACCESS_TOKEN_EXPIRE_MINUTES=30  # Token expiration time
DATABASE_URL=sqlite:///./outreach.db  # Database URL
```

## Troubleshooting

### Port Already in Use
```bash
# Find and kill process on port 8000
lsof -i :8000
kill -9 <PID>

# For port 3000
lsof -i :3000
kill -9 <PID>
```

### Database Issues
```bash
# Reset database
rm backend/outreach.db
# Restart backend to recreate
```

### Docker Issues
```bash
# Remove all containers and images
docker-compose down -v
docker system prune -a

# Rebuild from scratch
docker-compose build --no-cache
docker-compose up -d
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Open an issue on GitHub
- Contact: your-email@example.com
- Calendly: https://cal.com/nexa-lead-qng40v/15min

## Roadmap

- [ ] WebSocket support for real-time updates
- [ ] PostgreSQL support for production
- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] Email integration
- [ ] Slack/Teams integration
- [ ] Mobile app

---

**Built with ❤️ for modern sales teams**
