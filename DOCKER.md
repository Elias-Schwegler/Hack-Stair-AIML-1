# 🐳 Docker Guide - Geopard

Run the Geopard application using Docker on Windows, Linux, or macOS.

## Quick Start

### 1. Install Docker Desktop
- **Windows/macOS**: https://www.docker.com/products/docker-desktop
- **Linux**: https://docs.docker.com/engine/install/

### 2. Configure Environment
Edit `.env` with your Azure credentials:
```bash
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your_search_key_here
```

### 3. Start Application
**Windows:** Double-click `start-docker.bat`  
**Linux/macOS:** Run `./start-docker.sh`  
**Manual:** `docker compose up -d`

### 4. Access Application
- Web Interface: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Common Commands

```bash
# Start
docker compose up -d

# Stop
docker compose down

# View logs
docker compose logs -f

# Restart
docker compose restart

# Rebuild
docker compose build --no-cache && docker compose up -d

# Check status
docker compose ps

# Shell access
docker compose exec geopard /bin/bash
```

## Troubleshooting

### Port 8000 Already in Use
**Windows:**
```cmd
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Linux/macOS:**
```bash
lsof -ti:8000 | xargs kill -9
```

Or change port in `docker-compose.yml`: `"8080:8000"`

### Docker Not Running
Start Docker Desktop and wait for it to be ready.

### Build Fails
```bash
docker compose down
docker system prune -af
docker compose build --no-cache
docker compose up -d
```

### Check Environment Variables
```bash
docker compose exec geopard env | grep AZURE
```

### View Detailed Logs
```bash
docker compose logs -f --tail=100
```

### Permission Errors (Linux)
```bash
mkdir -p logs && chmod 777 logs
```

## Configuration

### Required Environment Variables
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint
- `AZURE_SEARCH_ENDPOINT` - Azure Search endpoint
- `AZURE_SEARCH_KEY` - Azure Search key

### Optional Variables (with defaults)
- `AZURE_OPENAI_API_VERSION=2024-12-01-preview`
- `AZURE_SEARCH_INDEX_NAME=geopard-rag-v2`
- `EMBEDDING_MODEL=text-embedding-3-large`
- `CHAT_MODEL=gpt-4o`

### Change Port
Edit `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Use port 8080 instead of 8000
```

## Windows-Specific Tips

### WSL 2 Incomplete
```powershell
wsl --install
```
Restart computer after installation.

### Virtualization Not Enabled
1. Restart computer
2. Enter BIOS (F2/F10/DEL)
3. Enable "Virtualization Technology" or "VT-x"
4. Save and restart

### Docker Desktop Won't Start
- Update Windows to latest version
- Enable WSL 2 feature
- Check Windows Firewall settings

## Production Deployment

### Security
- Never commit `.env` file
- Use Docker secrets or Azure Key Vault
- Run container as non-root (already configured)

### Scaling
```yaml
deploy:
  replicas: 3
  restart_policy:
    condition: on-failure
```

### Reverse Proxy (nginx example)
```nginx
server {
    listen 80;
    server_name geopard.example.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## What's Inside

**Dockerfile:**
- Python 3.11 slim base image
- Non-root user (UID 1000)
- Health checks enabled
- All dependencies pre-installed

**docker-compose.yml:**
- Service orchestration
- Environment variable management
- Port mapping (8000:8000)
- Volume mounts for logs
- Auto-restart policy

**Container Structure:**
```
/app
├── backend/         # RAG system
├── frontend/        # Web interface
├── location-tools/  # Location services
├── data/           # Geodata catalog (read-only)
└── logs/           # Application logs (volume)
```

## Help

- Check logs: `docker compose logs -f`
- Verify Docker: `docker info`
- Test health: `curl http://localhost:8000/health`
- Clean restart: `docker compose down && docker system prune -af && docker compose up -d`

For more information see [README.md](README.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
