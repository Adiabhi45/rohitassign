# Production Deployment Guide

## Prerequisites

- Python 3.8+
- Virtual environment
- Production server (Ubuntu/Debian recommended)
- Domain name (optional but recommended)
- SSL certificate (Let's Encrypt recommended)

## Step-by-Step Deployment

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv nginx supervisor -y

# Install system dependencies for image processing
sudo apt install libjpeg-dev zlib1g-dev -y
```

### 2. Application Setup

```bash
# Clone or upload your application
cd /var/www
sudo mkdir face-recognition
sudo chown $USER:$USER face-recognition
cd face-recognition

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs output reference_database

# Set up environment variables
cp .env.example .env
nano .env  # Edit with production values
```

### 3. Environment Configuration (.env)

```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Edit .env file
FLASK_ENV=production
SECRET_KEY=<generated-secret-key>
HOST=0.0.0.0
PORT=8000
```

### 4. Configure Gunicorn (Production WSGI Server)

Install Gunicorn:
```bash
pip install gunicorn
```

Create `gunicorn_config.py`:
```python
bind = "127.0.0.1:8000"
workers = 4
threads = 2
worker_class = "gthread"
timeout = 120
keepalive = 5
errorlog = "/var/www/face-recognition/logs/gunicorn-error.log"
accesslog = "/var/www/face-recognition/logs/gunicorn-access.log"
loglevel = "info"
```

### 5. Configure Supervisor (Process Manager)

Create `/etc/supervisor/conf.d/face-recognition.conf`:

```ini
[program:face-recognition]
directory=/var/www/face-recognition
command=/var/www/face-recognition/venv/bin/gunicorn -c gunicorn_config.py app:app
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/www/face-recognition/logs/supervisor.log
environment=PATH="/var/www/face-recognition/venv/bin"
```

Enable and start:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start face-recognition
```

### 6. Configure Nginx (Reverse Proxy)

Create `/etc/nginx/sites-available/face-recognition`:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    client_max_body_size 16M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }

    location /static {
        alias /var/www/face-recognition/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/face-recognition /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

### 8. Database Setup

```bash
# Initialize database
cd /var/www/face-recognition
source venv/bin/activate
python -c "from app import init_db; init_db()"

# Set proper permissions
sudo chown -R www-data:www-data /var/www/face-recognition
sudo chmod -R 755 /var/www/face-recognition
```

### 9. Firewall Configuration

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

### 10. Monitoring and Maintenance

Check application status:
```bash
sudo supervisorctl status face-recognition
```

View logs:
```bash
tail -f /var/www/face-recognition/logs/app.log
tail -f /var/www/face-recognition/logs/gunicorn-error.log
```

Restart application:
```bash
sudo supervisorctl restart face-recognition
```

## Security Checklist

- [ ] Strong SECRET_KEY generated
- [ ] FLASK_ENV set to 'production'
- [ ] SESSION_COOKIE_SECURE enabled (HTTPS)
- [ ] Firewall configured
- [ ] SSL certificate installed
- [ ] Database file permissions restricted
- [ ] .env file not in version control
- [ ] Regular backups configured
- [ ] Rate limiting implemented
- [ ] Email/SMS service configured for OTP

## Performance Optimization

1. **Enable Response Compression:**
   ```python
   # In app.py, add:
   from flask_compress import Compress
   Compress(app)
   ```

2. **Configure Caching:**
   ```python
   # Add Flask-Caching
   from flask_caching import Cache
   cache = Cache(app, config={'CACHE_TYPE': 'simple'})
   ```

3. **Use Redis for Sessions:**
   ```bash
   pip install redis flask-session
   ```

## Backup Strategy

```bash
# Create backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/face-recognition"
mkdir -p $BACKUP_DIR

# Backup database
cp /var/www/face-recognition/face_sketch.db $BACKUP_DIR/face_sketch_$DATE.db

# Backup reference images
tar -czf $BACKUP_DIR/reference_images_$DATE.tar.gz /var/www/face-recognition/reference_database

# Keep only last 7 days of backups
find $BACKUP_DIR -type f -mtime +7 -delete
```

Add to crontab:
```bash
0 2 * * * /usr/local/bin/backup-face-recognition.sh
```

## Troubleshooting

**Application won't start:**
```bash
# Check supervisor logs
sudo tail -f /var/www/face-recognition/logs/supervisor.log

# Check application logs
tail -f /var/www/face-recognition/logs/app.log
```

**502 Bad Gateway:**
- Check if Gunicorn is running: `sudo supervisorctl status`
- Check Nginx configuration: `sudo nginx -t`
- Check port availability: `sudo netstat -tulpn | grep 8000`

**High CPU usage:**
- Reduce Gunicorn workers
- Implement caching
- Optimize CLIP model loading

## Email/SMS Integration (Production OTP)

**SendGrid Example:**
```python
# In app.py
import sendgrid
from sendgrid.helpers.mail import Mail

def send_otp_email(email, otp_code):
    sg = sendgrid.SendGridAPIClient(api_key=os.getenv('SENDGRID_API_KEY'))
    message = Mail(
        from_email='noreply@yourdomain.com',
        to_emails=email,
        subject='Your OTP Code',
        html_content=f'<strong>Your OTP code is: {otp_code}</strong>'
    )
    sg.send(message)
```

**Twilio Example:**
```python
from twilio.rest import Client

def send_otp_sms(phone_number, otp_code):
    client = Client(
        os.getenv('TWILIO_ACCOUNT_SID'),
        os.getenv('TWILIO_AUTH_TOKEN')
    )
    message = client.messages.create(
        body=f'Your OTP code is: {otp_code}',
        from_=os.getenv('TWILIO_PHONE_NUMBER'),
        to=phone_number
    )
```

## Support

For issues or questions, refer to:
- Application logs: `/var/www/face-recognition/logs/`
- Nginx logs: `/var/log/nginx/`
- Supervisor logs: `/var/log/supervisor/`
