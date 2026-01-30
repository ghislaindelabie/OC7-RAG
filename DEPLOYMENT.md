# Deployment Guide - Ensuring Consistency

## Architecture: One Script, Multiple Entry Points

```
Manual Deployment              CI/CD (GitHub Actions)
        │                              │
        │                              │
        ▼                              ▼
deploy_to_server.sh          .github/workflows/deploy.yml
        │                              │
        │                              │
        └──────────────┬───────────────┘
                       │
                       ▼
              scripts/deploy.sh
               (SINGLE SOURCE OF TRUTH)
```

## Core Deployment Script

**Location:** `scripts/deploy.sh`

This is the **single source of truth** for deployment logic. Both manual and automated deployments use this script.

### What it does:
1. ✅ Tests SSH connection
2. ✅ Syncs files via rsync (with exclusions)
3. ✅ Creates/updates venv
4. ✅ Installs dependencies from requirements.txt
5. ✅ Stops old API gracefully
6. ✅ Configures environment (.env)
7. ✅ Starts new API
8. ✅ Verifies deployment

### Environment variables:
- `DEPLOY_HOST` - Server IP/hostname (required)
- `DEPLOY_USER` - SSH user (default: current user)
- `MISTRAL_API_KEY` - API key for Mistral
- `DEPLOY_DIR` - Target directory (default: ~/oc7-rag)

## Manual Deployment

**File:** `deploy_to_server.sh`

Interactive wrapper around `scripts/deploy.sh`:

```bash
# Interactive mode
./deploy_to_server.sh

# With arguments
./deploy_to_server.sh 192.168.1.100 myuser

# With environment variables
MISTRAL_API_KEY="xxx" ./deploy_to_server.sh 192.168.1.100
```

**What it adds:**
- Interactive prompts for server info
- Confirmation before deployment
- User-friendly output

**What it does NOT add:**
- No deployment logic (delegates to scripts/deploy.sh)

## CI/CD Deployment

**File:** `.github/workflows/deploy.yml`

Automated deployment on push to main:

```yaml
- name: Deploy using core script
  env:
    DEPLOY_HOST: ${{ secrets.HETZNER_HOST }}
    DEPLOY_USER: ${{ secrets.HETZNER_USER }}
    MISTRAL_API_KEY: ${{ secrets.MISTRAL_API_KEY }}
  run: |
    ./scripts/deploy.sh  # SAME SCRIPT as manual
```

**What it adds:**
- Runs tests first
- Uses GitHub Secrets for credentials
- Creates deployment summary
- Only runs on main branch

**What it does NOT add:**
- No deployment logic (delegates to scripts/deploy.sh)

## GitHub Secrets Setup

Required secrets in GitHub repository settings:

```
HETZNER_HOST          Your server IP or hostname
HETZNER_USER          SSH username
HETZNER_SSH_KEY       Private SSH key (for passwordless auth)
MISTRAL_API_KEY       Mistral API key
```

### Setting up SSH key authentication:

```bash
# 1. Generate SSH key pair (if you don't have one)
ssh-keygen -t ed25519 -C "github-actions"

# 2. Copy public key to server
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server

# 3. Add private key to GitHub Secrets
cat ~/.ssh/id_ed25519  # Copy this to HETZNER_SSH_KEY secret
```

## Testing Consistency

Both methods should produce identical results:

### Test 1: Manual deployment
```bash
./deploy_to_server.sh 192.168.1.100
curl http://192.168.1.100:8000/health
```

### Test 2: Trigger CI/CD manually
1. Go to GitHub Actions tab
2. Select "Deploy to Hetzner Server"
3. Click "Run workflow"
4. Check deployment summary

### Verify:
```bash
# Both should show same:
ssh user@server 'cd ~/oc7-rag && git log -1 --oneline'
ssh user@server 'cd ~/oc7-rag/venv && pip list | grep fastapi'
curl http://192.168.1.100:8000/api/v1/rag/info
```

## Troubleshooting

### Issue: Scripts don't match
**Solution:** They shouldn't have deployment logic! They both call `scripts/deploy.sh`

### Issue: Different Python versions
**Fix in `scripts/deploy.sh`:** Checks for Python 3.11+

### Issue: Different dependencies
**Fix:** Both use `requirements.txt` (same file)

### Issue: Manual works, CI/CD fails
**Check:**
1. GitHub Secrets configured?
2. SSH key has passwordless access?
3. Server firewall allows GitHub IPs?

### Issue: CI/CD works, manual fails
**Check:**
1. Same SSH key?
2. Same environment variables?
3. Run manual with `-x` flag to see commands:
   ```bash
   bash -x ./deploy_to_server.sh 192.168.1.100
   ```

## Deployment Checklist

- [ ] `scripts/deploy.sh` contains ALL deployment logic
- [ ] `deploy_to_server.sh` only handles user input → calls deploy.sh
- [ ] `.github/workflows/deploy.yml` only handles GitHub → calls deploy.sh
- [ ] Same rsync exclusions in deploy.sh
- [ ] Same Python version check in deploy.sh
- [ ] Same pip install command in deploy.sh
- [ ] Same API start command in deploy.sh
- [ ] Both use requirements.txt (not pyproject.toml on server)
- [ ] GitHub Secrets match manual environment variables

## Benefits of This Architecture

✅ **Single Source of Truth:** Change deployment logic in one place
✅ **Consistency:** Manual and CI/CD behave identically  
✅ **Testable:** Can test deploy.sh locally before committing
✅ **Debuggable:** Same script logs for both methods
✅ **Maintainable:** One script to maintain, not two

## When to Modify

**Add/change deployment step:**
→ Edit `scripts/deploy.sh` only

**Add GitHub Actions feature:**
→ Edit `.github/workflows/deploy.yml` (but call deploy.sh)

**Add manual deployment feature:**
→ Edit `deploy_to_server.sh` (but call deploy.sh)
