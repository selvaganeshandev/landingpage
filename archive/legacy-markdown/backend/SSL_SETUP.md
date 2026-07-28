# SSL/TLS Setup for LLM Monitor Backend

This guide explains how to enable SSL/TLS for the Django backend.

## Quick Start

### 1. Generate SSL Certificates

For development, generate a self-signed certificate:

```bash
cd backend
./generate_ssl_cert.sh
```

This will create:
- `ssl/server.crt` - SSL certificate
- `ssl/server.key` - Private key

### 2. Start Server with SSL

```bash
cd backend
./start-ssl-server.sh
```

The server will start on `https://localhost:8000` (or the port specified in your `.env` file).

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# Enable SSL/TLS
USE_TLS=True

# SSL Certificate paths
SSL_CERTIFICATE_PATH=ssl/server.crt
SSL_PRIVATE_KEY_PATH=ssl/server.key

# Security settings (for production)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

### Django Settings

The following SSL-related settings are available in `llm_monitor/settings.py`:

- `USE_TLS`: Enable/disable TLS (default: False)
- `SECURE_SSL_REDIRECT`: Redirect HTTP to HTTPS (default: False)
- `SESSION_COOKIE_SECURE`: Only send session cookies over HTTPS (default: False)
- `CSRF_COOKIE_SECURE`: Only send CSRF cookies over HTTPS (default: False)
- `SECURE_HSTS_SECONDS`: HSTS max-age in seconds (default: 0, disabled)
- `SECURE_HSTS_INCLUDE_SUBDOMAINS`: Include subdomains in HSTS (default: False)
- `SECURE_HSTS_PRELOAD`: Enable HSTS preload (default: False)

## Production Setup

### Using Gunicorn with SSL

The `start-ssl-server.sh` script automatically uses Gunicorn if available:

```bash
gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --threads 2 \
    --keyfile ssl/server.key \
    --certfile ssl/server.crt \
    llm_monitor.wsgi:application
```

### Using Proper SSL Certificates

For production, use certificates from a trusted Certificate Authority (CA):

1. **Let's Encrypt (Free)**:
   ```bash
   sudo certbot certonly --standalone -d yourdomain.com
   ```
   Certificates will be in `/etc/letsencrypt/live/yourdomain.com/`

2. **Update `.env`**:
   ```env
   SSL_CERTIFICATE_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
   SSL_PRIVATE_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem
   USE_TLS=True
   ```

3. **Use a Reverse Proxy (Recommended)**:
   - Nginx or Apache in front of Gunicorn
   - SSL termination at the proxy level
   - Better performance and security

### Nginx Configuration Example

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Development Notes

### Self-Signed Certificate Warnings

When using self-signed certificates, browsers will show security warnings. This is normal and expected. You can:

1. **Chrome/Edge**: Click "Advanced" → "Proceed to localhost (unsafe)"
2. **Firefox**: Click "Advanced" → "Accept the Risk and Continue"
3. **Add Exception**: Add the certificate to your browser's trusted certificates

### Testing SSL

```bash
# Test SSL connection
curl -k https://localhost:8000/api/health/

# Test with certificate verification (will fail for self-signed)
curl --cacert ssl/server.crt https://localhost:8000/api/health/
```

## Troubleshooting

### Certificate Not Found

If you see "certificate not found" errors:
1. Run `./generate_ssl_cert.sh` to create certificates
2. Check that `SSL_CERTIFICATE_PATH` and `SSL_PRIVATE_KEY_PATH` in `.env` point to the correct files

### Port Already in Use

If port 8000 is already in use:
1. Change the port in your `.env`: `PORT=8443`
2. Or stop the existing server

### CORS Issues with HTTPS

If you get CORS errors when accessing from HTTPS frontend:
1. Make sure `USE_TLS=True` in backend `.env`
2. Add your HTTPS frontend URL to `CORS_ALLOWED_ORIGINS` in settings
3. The script automatically adds common HTTPS origins when `USE_TLS=True`

### Gunicorn Not Found

If Gunicorn is not installed:
```bash
pip install gunicorn
```

Or the script will fall back to Django's `runserver_plus` (requires `django-extensions`).

## Security Best Practices

1. **Never commit private keys** to version control
2. **Use strong certificates** in production (Let's Encrypt or commercial CA)
3. **Enable HSTS** in production for better security
4. **Use a reverse proxy** (Nginx/Apache) for SSL termination in production
5. **Keep certificates updated** and renew before expiration
6. **Monitor certificate expiration** and set up auto-renewal

## Files Created

- `ssl/server.crt` - SSL certificate (self-signed for dev)
- `ssl/server.key` - Private key (keep secure!)
- `generate_ssl_cert.sh` - Certificate generation script
- `start-ssl-server.sh` - SSL-enabled server startup script

