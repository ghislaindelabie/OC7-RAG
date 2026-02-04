# Deployment Status & Guide - OC7 RAG API

> **Last Updated**: 2026-02-04
> **Current Status**: ✅ v0.4.0 - Docker CI/CD + Web Chat Interface
> **Deployment Method**: 🐳 Docker Compose (Recommended)

---

## Production Environment

### Server Details
- **Host**: hetzner3-oc7api (2a01:4f8:c2c:5fbe::1)
- **User**: oc7api (dedicated, minimal permissions)
- **Location**: `/home/oc7api/oc7-rag-docker`
- **Python**: 3.12.3 (in Docker container)
- **Docker**: 29.1.3 + Compose v5.0.0
- **Port**: 8000

### Current Deployment
- **Method**: 🐳 **Docker container** (CI/CD via GitHub Actions)
- **Image**: `ghcr.io/ghislaindelabie/oc7-rag-api:latest` (1.45GB)
- **Status**: Running, healthy
- **Index Loaded**: Yes ✓ (auto-rebuilt on first start)
- **LLM Available**: Yes ✓
- **Health Check**: http://localhost:8000/health (accessible from server)

### SSH Access
```bash
# Direct connection
ssh oc7api@2a01:4f8:c2c:5fbe::1

# Via alias
ssh hetzner3-oc7api

# Check API status
ssh hetzner3-oc7api 'curl -s http://localhost:8000/health | python3 -m json.tool'

# View logs
ssh hetzner3-oc7api 'tail -f ~/oc7-rag/api.log'

# Restart API
ssh hetzner3-oc7api 'kill $(cat ~/oc7-rag/api.pid) && cd ~/oc7-rag && source venv/bin/activate && nohup python scripts/run_api.py > api.log 2>&1 & echo $! > api.pid'
```

---

## Deployment Methods

### 🐳 Method 1: Docker Deployment (Recommended)

**Current deployment method** - Uses Docker Compose for consistent, reproducible deployments.

#### Quick Start
```bash
# Clone/pull latest code on server
ssh hetzner3-oc7api
cd ~/oc7-rag-docker
git pull

# Start with Docker Compose
docker compose up -d

# View logs
docker compose logs -f

# Check status
docker compose ps
curl http://localhost:8000/health
```

#### Production Deployment (GHCR)
```bash
# Using production compose file (pulls pre-built image from GitHub Container Registry)
cd ~/oc7-rag-docker
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs --tail=50
```

#### Docker Features
- **Auto-rebuild**: Downloads data and builds FAISS index on first start (~3-5 min)
- **Persistent volumes**: Data survives container restarts
- **Health checks**: Container orchestration ready
- **Multi-stage build**: Optimized image size (1.45GB)
- **Non-root user**: Security best practice

#### Environment Variables
```bash
# Required
MISTRAL_API_KEY=your-mistral-api-key

# Optional
AUTO_REBUILD_INDEX=true  # Auto-rebuild if index missing (default: true)
```

---

### 🚀 Method 2: CI/CD Deployment (Automated)

**Automatic deployment** on push to `main` branch via GitHub Actions.

#### Workflow
```
Push to main → Tests → Build Docker image → Push to GHCR → Deploy to server
```

#### GitHub Secrets Required
- `HETZNER_HOST`: hetzner3-oc7api
- `HETZNER_USER`: oc7api
- `HETZNER_SSH_KEY`: Private SSH key content
- `MISTRAL_API_KEY`: Mistral API key

#### Workflow File
`.github/workflows/deploy.yml` - Handles test → build → push → deploy pipeline

#### Trigger Deployment
1. **Automatic**: Push/merge to `main` branch
2. **Manual**: GitHub Actions tab → "Deploy to Hetzner Server" → "Run workflow"

#### Monitor Deployment
```bash
# View GitHub Actions logs in browser
# Or check server directly:
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && docker compose logs --tail=100'
```

---

### 📦 Method 3: Legacy Manual Deployment (Deprecated)

> **Note**: This method is deprecated. Use Docker deployment instead.

<details>
<summary>Click to expand legacy manual deployment instructions</summary>

```bash
# Interactive
./deploy_to_server.sh hetzner3-oc7api oc7api

# Non-interactive
export DEPLOY_HOST=hetzner3-oc7api
export DEPLOY_USER=oc7api
export MISTRAL_API_KEY='your_key'
./scripts/deploy.sh
```

This method deploys without Docker using Python venv. **Not recommended for new deployments.**

</details>

---

## Deployment Architecture

### Single Source of Truth Pattern

```
Manual Docker              CI/CD (GitHub Actions)
     │                              │
     │                              │
     ▼                              ▼
docker compose up        .github/workflows/deploy.yml
     │                              │
     │                              │
     └──────────────┬───────────────┘
                    │
                    ▼
         Dockerfile + docker-compose.yml
          (SINGLE SOURCE OF TRUTH)
```

**Benefits**:
- ✅ Consistent deployments across environments
- ✅ Reproducible builds (Docker image)
- ✅ Version-controlled configuration
- ✅ Easy rollback (previous image tags)
- ✅ Isolated dependencies

---

## User Setup

### oc7api User
- **Created**: 2026-01-29
- **UID/GID**: 1003/1003
- **Groups**: oc7api, docker
- **Home**: `/home/oc7api`
- **Shell**: `/bin/bash`
- **SSH Key**: Same as ghislain user (~/.ssh/id_ghislain)

### Security
- ✅ Minimal permissions (no sudo access)
- ✅ Cannot modify system files
- ✅ Cannot access other users' files
- ✅ Can only manage own home directory
- ✅ Can bind to ports >1024 (8000)
- ✅ Docker group access for container management
- ✅ Principle of least privilege

---

## Dependency Management

### Local Development
```bash
# 1. Conda for ML packages
conda env create -f environment.yml
conda activate OC7

# 2. uv for small packages
pip install uv
uv pip install -e .

# 3. Dev dependencies
uv pip install -e ".[dev]"
```

### Server (Production)
```bash
# Traditional pip + venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Files**:
- `environment.yml` - Conda packages (pandas, numpy, faiss, jupyter)
- `pyproject.toml` - uv packages (fastapi, langchain, pydantic)
- `requirements.txt` - Server deployment (all packages)

---

## API Endpoints Status

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /` | ✅ Working | **NEW** Web chat interface |
| `GET /health` | ✅ Working | Returns healthy (index loaded, LLM available) |
| `GET /api/v1/rag/info` | ✅ Working | Returns system info |
| `POST /api/v1/ask` | ✅ Working | RAG query with 3 methods (basic, hybrid, advanced) |
| `POST /api/v1/rebuild` | ✅ Working | Index rebuild functionality implemented |

### Health Check Response
```json
{
    "status": "healthy",
    "index_loaded": true,
    "index_size": 8542,
    "llm_available": true,
    "timestamp": "2026-01-30T16:37:53.093122+00:00"
}
```

**Status**: All endpoints fully functional. v0.4.0 complete.

---

## Testing

### Local Tests
```bash
# Run all API tests
pytest tests/test_api.py -v

# Current status: 31+ tests passing
```

### Server Testing
```bash
# Via SSH tunnel
ssh -L 8000:localhost:8000 hetzner3-oc7api

# Then on local machine
curl http://localhost:8000/health
curl http://localhost:8000/docs
open http://localhost:8000  # Chat interface
```

---

## Troubleshooting

### Docker-Specific Issues

**Container fails to start**:
```bash
# Check logs
docker compose logs

# Check if port already in use
sudo lsof -i :8000

# Restart container
docker compose down
docker compose up -d
```

**Index not building**:
```bash
# Check AUTO_REBUILD_INDEX is set to true
docker compose config | grep AUTO_REBUILD_INDEX

# Check logs for download/build errors
docker compose logs --tail=100 | grep -i error

# Manual rebuild (inside container)
docker compose exec oc7-rag-api python scripts/rebuild_index.py
```

**Out of disk space**:
```bash
# Check Docker disk usage
docker system df

# Clean up old images/containers
docker system prune -a

# Check volume size
docker volume inspect oc7-rag-docker_oc7-rag-data
```

### CI/CD Issues

**GitHub Actions fails**:
1. Check GitHub Secrets are configured correctly
2. Verify SSH key has access: `ssh -i <key> oc7api@hetzner3-oc7api`
3. Check workflow logs in GitHub Actions tab
4. Verify server has enough disk space

**Image push fails**:
- Check GitHub Container Registry permissions
- Verify `GITHUB_TOKEN` has package write access

### General Issues

**Health check returns unhealthy**:
```bash
# Check if index loaded
curl http://localhost:8000/health | python3 -m json.tool

# Check container logs
docker compose logs --tail=50

# Check MISTRAL_API_KEY is set
docker compose exec oc7-rag-api env | grep MISTRAL
```

**External Access**:
- **Issue**: Port 8000 not accessible from outside
- **Cause**: Not firewall (UFW disabled) - likely Hetzner network/IPv6 configuration
- **Workaround**: SSH tunnel (secure) or setup nginx reverse proxy (for public access)
- **Priority**: Low (API accessible from server, SSH tunnel works)

**SSH tunnel for local access**:
```bash
# Create tunnel
ssh -L 8000:localhost:8000 hetzner3-oc7api

# Then open browser
open http://localhost:8000
```

---

## Version Status: v0.4.0 ✅ COMPLETE

### ✅ Track A: API Development (DONE)
- [x] FastAPI structure with 5 endpoints
- [x] Pydantic schemas for validation
- [x] Singleton RAG service pattern
- [x] POST /api/v1/ask with 3 RAG methods
- [x] POST /api/v1/rebuild with data download
- [x] Comprehensive error handling
- [x] 31+ tests passing

### ✅ Track B: Evaluation & Testing (DONE)
- [x] 56 annotated test questions
- [x] LLM-as-Judge evaluation
- [x] Unit tests (indexation + retriever)

### ✅ Track C: Docker & CI/CD (DONE)
- [x] Multi-stage Dockerfile (1.45GB image)
- [x] docker-compose.yml (local/dev)
- [x] docker-compose.prod.yml (production/GHCR)
- [x] .dockerignore (optimized build context)
- [x] CI/CD workflow (test → build → push → deploy)
- [x] Docker installed on server
- [x] Manual deployment tested

### ✅ Track D: Web Chat Interface (DONE)
- [x] Modern web UI at GET /
- [x] Support for 3 RAG methods
- [x] Source document display
- [x] Health status indicator
- [x] Responsive mobile layout

### ⏳ Remaining Tasks
- [ ] Technical report (PDF)
- [ ] PowerPoint presentation
- [ ] Demo scenarios

---

## Deployment History

| Date | User | Action | Result |
|------|------|--------|--------|
| 2026-01-29 19:34 | ghislain | Initial deployment | ✅ Success |
| 2026-01-29 20:43 | oc7api | Created dedicated user | ✅ Success |
| 2026-01-29 20:47 | oc7api | First deployment | ✅ Success |
| 2026-01-29 20:48 | ghislain | Cleanup old deployment | ✅ Complete |
| 2026-01-30 16:37 | oc7api | Docker container deployment | ✅ Success |

---

## Quick Reference

### 🐳 Docker Commands (Current)

```bash
# Start container
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && docker compose up -d'

# Stop container
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && docker compose down'

# Restart container
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && docker compose restart'

# View logs (last 50 lines)
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && docker compose logs --tail=50'

# Follow logs live
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && docker compose logs -f'

# Check container status
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && docker compose ps'

# Execute command in container
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && docker compose exec oc7-rag-api <command>'

# Rebuild and restart (force fresh build)
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && docker compose up -d --build --force-recreate'

# Remove volumes (fresh start)
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && docker compose down -v && docker compose up -d'
```

### 🧪 Testing Commands

```bash
# Test health endpoint
ssh hetzner3-oc7api 'curl -s localhost:8000/health | python3 -m json.tool'

# Test chat interface (via SSH tunnel)
ssh -L 8000:localhost:8000 hetzner3-oc7api
# Then: open http://localhost:8000

# Test RAG query
ssh hetzner3-oc7api 'curl -X POST http://localhost:8000/api/v1/ask -H "Content-Type: application/json" -d "{\"question\": \"Concerts à Chambéry?\"}"'

# Check API info
ssh hetzner3-oc7api 'curl -s localhost:8000/api/v1/rag/info | python3 -m json.tool'
```

### 🔧 Maintenance Commands

```bash
# Check disk usage
ssh hetzner3-oc7api 'df -h'
ssh hetzner3-oc7api 'docker system df'

# Clean up Docker
ssh hetzner3-oc7api 'docker system prune -a'

# Check Docker images
ssh hetzner3-oc7api 'docker images | grep oc7-rag'

# Pull latest image
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && docker compose pull'

# Update and restart
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && git pull && docker compose pull && docker compose up -d'
```

### Documentation

**This File**: Consolidated deployment guide (merged from DEPLOYMENT.md, QUICK_START_DEPLOYMENT.md, SERVER_TEST.md)

**Related Documentation**:
- `README.md` - Main project documentation
- `VERSION_HISTORY.md` - Version changelog
- `PROJECT_FINALIZATION_PLAN.md` - Finalization roadmap
- `docs/reference/` - Technical reference docs
  - `SETUP.md` - Local + server setup
  - `DEPENDENCY_MANAGEMENT.md` - Dependency strategy
  - `CHATBOT_INTERFACE.md` - Web interface guide
- `docs/future/` - Future enhancements
  - `API_AUTHENTICATION.md` - Authentication guide
  - `VECTOR_STORE_MIGRATION.md` - Vector store migration

**Deployment Files**:
- `Dockerfile` - Multi-stage Docker build
- `docker-compose.yml` - Local/dev deployment
- `docker-compose.prod.yml` - Production deployment (GHCR)
- `.dockerignore` - Build context exclusions
- `.github/workflows/deploy.yml` - CI/CD workflow
- `deploy_to_server.sh` - Legacy manual deployment (deprecated)

---

## Monitoring

### Health Checks
```bash
# Simple check
curl -f http://localhost:8000/health || echo "API down"

# Detailed check
curl -s http://localhost:8000/health | python3 -m json.tool
```

### Logs
```bash
# Recent errors
ssh hetzner3-oc7api 'grep -i error ~/oc7-rag/api.log | tail -20'

# Recent requests
ssh hetzner3-oc7api 'grep "HTTP/1.1" ~/oc7-rag/api.log | tail -20'

# API startup
ssh hetzner3-oc7api 'grep "Starting up" ~/oc7-rag/api.log'

# Docker logs
ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && sg docker "docker compose logs --tail=100"'
```

---

## Rollback Procedure

If deployment fails:

1. **Check logs**:
   ```bash
   ssh hetzner3-oc7api 'tail -50 ~/oc7-rag/api.log'
   # Or for Docker:
   ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && sg docker "docker compose logs --tail=50"'
   ```

2. **Stop broken API**:
   ```bash
   ssh hetzner3-oc7api 'kill $(cat ~/oc7-rag/api.pid) 2>/dev/null'
   # Or for Docker:
   ssh hetzner3-oc7api 'cd ~/oc7-rag-docker && sg docker "docker compose down"'
   ```

3. **Redeploy previous version**:
   ```bash
   # Checkout previous commit locally
   git checkout <previous-commit>

   # Deploy
   ./deploy_to_server.sh hetzner3-oc7api oc7api
   ```

4. **Or restore from backup** (if you created one):
   ```bash
   ssh hetzner3-oc7api 'mv ~/oc7-rag.backup ~/oc7-rag'
   ```

---

## Contact & Support

- **User**: Ghislain
- **Server Admin**: Ghislain (via root@2a01:4f8:c2c:5fbe::1)
- **API User**: oc7api (dedicated, no sudo)
- **Documentation**: This file + other docs in project root
