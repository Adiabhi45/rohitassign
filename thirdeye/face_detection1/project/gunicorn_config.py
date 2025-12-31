bind = "127.0.0.1:8000"
workers = 4  # (2 * CPU cores) + 1
threads = 2
worker_class = "gthread"
timeout = 120  # Increase for ML model loading
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

# Logging
errorlog = "logs/gunicorn-error.log"
accesslog = "logs/gunicorn-access.log"
loglevel = "info"

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190
