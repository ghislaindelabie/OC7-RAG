# Quick Start - Which Script to Use?

## TL;DR

**For testing on server NOW (manual):**
```bash
./deploy_to_server.sh YOUR_SERVER_IP
```

**For automatic deployment later (CI/CD):**
Configure GitHub Secrets once, then push to main → auto-deploys

---

## Detailed Guide

### Scenario 1: Manual Deployment (Testing Now)

**Use:** `./deploy_to_server.sh`

**Step-by-step:**

```bash
# 1. Make sure you have the Mistral API key
#    Check your local .env file or get it from Mistral console
cat .env | grep MISTRAL_API_KEY

# 2. Run deployment script (interactive)
./deploy_to_server.sh

# It will ask:
#   - Server IP: YOUR_SERVER_IP
#   - SSH user: YOUR_USERNAME (or press Enter for current user)
#   - Mistral API key: paste_your_key_here

# 3. Script does everything automatically:
#   ✓ Tests SSH connection
#   ✓ Copies files
#   ✓ Installs dependencies
#   ✓ Starts API
#   ✓ Verifies it works
```

**Non-interactive mode (if you prefer):**
```bash
# Option A: With arguments
./deploy_to_server.sh 192.168.1.100 myuser

# Option B: With environment variables
export MISTRAL_API_KEY="sk-proj-xxxx"
./deploy_to_server.sh 192.168.1.100

# Option C: One-liner
MISTRAL_API_KEY="sk-proj-xxxx" ./deploy_to_server.sh 192.168.1.100
```

---

### Scenario 2: Automatic Deployment (CI/CD - Later)

**Use:** GitHub Actions (no script to run manually)

**One-time setup:**

1. **Add SSH key to server:**
```bash
# On your local machine
ssh-copy-id your_user@your_server
# Test: ssh your_user@your_server (should not ask password)
```

2. **Configure GitHub Secrets** (Settings → Secrets → Actions):
```
Name: HETZNER_HOST
Value: your_server_ip

Name: HETZNER_USER  
Value: your_username

Name: HETZNER_SSH_KEY
Value: [paste your private SSH key]
# Get it with: cat ~/.ssh/id_rsa or cat ~/.ssh/id_ed25519

Name: MISTRAL_API_KEY
Value: sk-proj-xxxx
```

3. **That's it!** Now every push to `main` branch auto-deploys.

---

## Environment Variables - Where They Live

### 1. Local Development (.env file)

**Location:** `/Users/ghislaindelabie/.../OC7 - RAG/.env`

**Purpose:** When you run API locally on your Mac

**Content:**
```bash
MISTRAL_API_KEY=sk-proj-xxxx
```

**Created:** Manually by you

**Used by:** `python scripts/run_api.py` (local testing)

---

### 2. Server (.env file)

**Location:** `~/oc7-rag/.env` (on Hetzner server)

**Purpose:** When API runs on server

**Content:**
```bash
MISTRAL_API_KEY=sk-proj-xxxx
```

**Created:** Automatically by deployment script

**Used by:** `python scripts/run_api.py` (on server)

**Important:** Deployment script creates this file from MISTRAL_API_KEY environment variable

---

### 3. CI/CD (GitHub Secrets)

**Location:** GitHub repository settings

**Purpose:** Used by GitHub Actions to deploy

**Content:**
- `HETZNER_HOST`
- `HETZNER_USER`
- `HETZNER_SSH_KEY`
- `MISTRAL_API_KEY`

**Created:** Manually in GitHub UI

**Used by:** `.github/workflows/deploy.yml`

---

## How Mistral API Key Flows

### Manual Deployment:
```
You type key → deploy_to_server.sh → MISTRAL_API_KEY env var → 
scripts/deploy.sh → Creates .env on server → API reads .env
```

### CI/CD Deployment:
```
GitHub Secret → GitHub Actions → MISTRAL_API_KEY env var →
scripts/deploy.sh → Creates .env on server → API reads .env
```

### Result:
Both create the **same .env file** on server ✅

---

## Common Questions

### Q: Do I need to manually create .env on server?
**A:** No! The deployment script does it for you.

### Q: Where do I get the Mistral API key?
**A:** Check your local `.env` file or get from https://console.mistral.ai/

### Q: Can I use the same API key locally and on server?
**A:** Yes! Same key everywhere is fine.

### Q: What if I want to change the API key later?
**A:** 
- Local: Edit `.env` file
- Server: Re-run deployment OR manually edit `~/oc7-rag/.env` on server
- CI/CD: Update GitHub Secret

### Q: Should I commit .env file to git?
**A:** NO! It's already in `.gitignore`

### Q: What if deployment fails because of missing API key?
**A:** API will start but show warnings. Set key and restart:
```bash
ssh your_server
cd ~/oc7-rag
echo "MISTRAL_API_KEY=sk-proj-xxxx" > .env
kill $(cat api.pid)
nohup python scripts/run_api.py > api.log 2>&1 &
```

---

## Test Right Now

**Easiest way to test:**

```bash
# 1. Check you have the API key locally
cat .env

# 2. Deploy (interactive prompts)
./deploy_to_server.sh

# 3. Enter when asked:
#    Server IP: [your server IP]
#    User: [your username or press Enter]
#    API key: [paste from .env file]

# 4. Wait ~2 minutes

# 5. Test from your Mac
curl http://YOUR_SERVER_IP:8000/health
```

**That's it!**

---

## What Each Script Does

| Script | You Use It? | What It Does |
|--------|------------|--------------|
| `deploy_to_server.sh` | ✅ YES (manual) | Asks you questions, calls deploy.sh |
| `scripts/deploy.sh` | ❌ NO (called automatically) | Does actual deployment work |
| `.github/workflows/deploy.yml` | ❌ NO (auto-runs on push) | Triggers deploy.sh on main push |

**Rule of thumb:** 
- Want to deploy now? → `./deploy_to_server.sh`
- Want auto-deploy? → Configure GitHub Secrets
- Modifying deployment? → Edit `scripts/deploy.sh`

