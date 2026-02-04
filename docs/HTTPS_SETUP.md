# HTTPS Setup Guide - OC7 RAG System

**Status**: Planned for future implementation
**Target domain**: `oc7-rag.delabie.tech` (or similar subdomain)
**Last updated**: 2026-02-04

---

## Overview

This guide documents the process for adding HTTPS support to the OC7 RAG API using Let's Encrypt free SSL certificates. Implementation will be done once the subdomain is configured at delabie.tech.

## Prerequisites

Before implementing HTTPS, ensure:

1. **DNS Configuration**:
   - Create A record: `oc7-rag.delabie.tech` → `188.34.205.146`
   - Wait for DNS propagation (typically 5-30 minutes)
   - Verify with: `dig oc7-rag.delabie.tech` or `nslookup oc7-rag.delabie.tech`

2. **Firewall Rules**:
   - Port 80 (HTTP) open for Let's Encrypt validation
   - Port 443 (HTTPS) open for secure traffic
   - Existing port 8000 can remain for direct API access (optional)

3. **Server Access**:
   - SSH access to Hetzner server: `oc7api@188.34.205.146`
   - sudo privileges for installing packages

---

## Implementation Options

### Option 1: Nginx Reverse Proxy with Certbot (Recommended)

This is the simplest and most maintainable approach for a single server deployment.

#### Step 1: Install Nginx and Certbot

```bash
ssh oc7api@188.34.205.146

# Update package lists
sudo apt update

# Install Nginx and Certbot
sudo apt install nginx certbot python3-certbot-nginx -y
```

#### Step 2: Configure Nginx Reverse Proxy

Create Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/oc7-rag
```

Add the following configuration:

```nginx
# HTTP server block - will be auto-upgraded to HTTPS by Certbot
server {
    listen 80;
    listen [::]:80;
    server_name oc7-rag.delabie.tech;

    # Proxy all requests to Docker container
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Increase timeouts for long-running operations (like rebuild)
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

#### Step 3: Enable Site

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/oc7-rag /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Enable Nginx to start on boot
sudo systemctl enable nginx
```

#### Step 4: Obtain SSL Certificate

```bash
# Run Certbot - it will automatically configure HTTPS
sudo certbot --nginx -d oc7-rag.delabie.tech

# Follow the prompts:
# - Enter email address for renewal notifications
# - Agree to Terms of Service
# - Choose whether to redirect HTTP to HTTPS (recommended: yes)
```

Certbot will:
- Obtain a free SSL certificate from Let's Encrypt
- Modify Nginx configuration to use HTTPS
- Set up automatic certificate renewal

#### Step 5: Verify Setup

```bash
# Check certificate status
sudo certbot certificates

# Test auto-renewal
sudo certbot renew --dry-run

# Verify HTTPS is working
curl https://oc7-rag.delabie.tech/health
```

#### Step 6: Test in Browser

Visit:
- `https://oc7-rag.delabie.tech/` - Web interface
- `https://oc7-rag.delabie.tech/docs` - API documentation
- `https://oc7-rag.delabie.tech/health` - Health check

You should see a valid SSL certificate with no browser warnings.

---

### Option 2: Docker Compose with Nginx Container

Alternative approach using containerized Nginx (more complex but more portable).

#### Updated docker-compose.prod.yml

Add the following services to your existing `docker-compose.prod.yml`:

```yaml
services:
  # Existing API service
  api:
    # ... existing configuration ...
    expose:
      - "8000"  # Change from ports to expose (internal only)
    # Remove the ports: section since Nginx will handle external access

  # Nginx reverse proxy
  nginx:
    image: nginx:alpine
    container_name: oc7-rag-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - certbot-etc:/etc/letsencrypt
      - certbot-var:/var/lib/letsencrypt
      - certbot-www:/var/www/certbot
    depends_on:
      - api
    networks:
      - oc7-network

  # Certbot for SSL certificates
  certbot:
    image: certbot/certbot
    container_name: oc7-rag-certbot
    volumes:
      - certbot-etc:/etc/letsencrypt
      - certbot-var:/var/lib/letsencrypt
      - certbot-www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
    networks:
      - oc7-network

volumes:
  certbot-etc:
  certbot-var:
  certbot-www:

networks:
  oc7-network:
    driver: bridge
```

#### Nginx Configuration Files

Create `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    sendfile on;
    keepalive_timeout 65;

    include /etc/nginx/conf.d/*.conf;
}
```

Create `nginx/conf.d/oc7-rag.conf`:

```nginx
server {
    listen 80;
    server_name oc7-rag.delabie.tech;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name oc7-rag.delabie.tech;

    ssl_certificate /etc/letsencrypt/live/oc7-rag.delabie.tech/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/oc7-rag.delabie.tech/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

#### Initial Certificate Setup

```bash
# First, get the initial certificate (before starting HTTPS)
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email \
  -d oc7-rag.delabie.tech

# Then start all services
docker compose -f docker-compose.prod.yml up -d
```

---

## Certificate Renewal

### Option 1 (Native Nginx)

Certbot automatically sets up a systemd timer for renewal:

```bash
# Check renewal timer status
sudo systemctl status certbot.timer

# Manual renewal test
sudo certbot renew --dry-run

# Force renewal (if needed)
sudo certbot renew --force-renewal
```

### Option 2 (Docker)

The certbot container automatically attempts renewal every 12 hours.

```bash
# Force manual renewal
docker compose -f docker-compose.prod.yml run --rm certbot renew

# Reload Nginx after renewal
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

---

## CI/CD Integration

Once HTTPS is configured, update `.github/workflows/deploy.yml` health check URLs:

```yaml
# Change from:
curl -sf http://localhost:8000/health

# To (if using Nginx on same server):
curl -sf https://oc7-rag.delabie.tech/health

# Or keep localhost check since deployment runs on server:
curl -sf http://localhost:8000/health  # Still valid - checks container directly
```

The localhost check can remain unchanged since the deployment script runs on the server itself and can access the container directly.

---

## Security Considerations

1. **API Key Protection**: HTTPS encrypts the Mistral API key in transit
2. **CORS**: Update CORS settings in `src/api/main.py` if needed:
   ```python
   origins = [
       "https://oc7-rag.delabie.tech",
       "http://localhost:3000",  # Keep for development
   ]
   ```
3. **HSTS**: Consider adding HTTP Strict Transport Security header
4. **Rate Limiting**: Consider adding Nginx rate limiting for production

---

## Troubleshooting

### Certificate Acquisition Failed

```bash
# Check DNS propagation
dig oc7-rag.delabie.tech
nslookup oc7-rag.delabie.tech

# Check port 80 is accessible
sudo netstat -tlnp | grep :80

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log

# Check Certbot logs
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

### Certificate Renewal Issues

```bash
# Test renewal in verbose mode
sudo certbot renew --dry-run --verbose

# Check certificate expiry
sudo certbot certificates
```

### Nginx Configuration Issues

```bash
# Test configuration
sudo nginx -t

# Reload configuration
sudo systemctl reload nginx

# Restart Nginx
sudo systemctl restart nginx

# Check Nginx status
sudo systemctl status nginx
```

---

## Implementation Checklist

When ready to implement:

- [ ] Create DNS A record: `oc7-rag.delabie.tech` → `188.34.205.146`
- [ ] Wait for DNS propagation (verify with `dig` or `nslookup`)
- [ ] Choose implementation option (Option 1 recommended)
- [ ] Install Nginx and Certbot (Option 1) or update docker-compose (Option 2)
- [ ] Configure Nginx reverse proxy
- [ ] Obtain SSL certificate with Certbot
- [ ] Test HTTPS access to all endpoints
- [ ] Verify auto-renewal is configured
- [ ] Update any hardcoded HTTP URLs in documentation
- [ ] Update CORS settings if needed
- [ ] Test web interface and API docs over HTTPS
- [ ] Monitor certificate expiry (Let's Encrypt certs valid for 90 days)

---

## References

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Certbot Documentation](https://certbot.eff.org/)
- [Nginx Reverse Proxy Guide](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [SSL Configuration Generator](https://ssl-config.mozilla.org/)

---

## Notes

- Let's Encrypt certificates are valid for 90 days
- Automatic renewal typically happens at 60 days
- Rate limit: 50 certificates per registered domain per week
- Certificates are free but domain registration is required
- HTTPS is required for production deployment best practices
