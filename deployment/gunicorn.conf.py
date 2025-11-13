import multiprocessing
import os

# Read from env with sane defaults
workers = int(os.getenv("GUNICORN_WORKERS", str(multiprocessing.cpu_count() * 2 + 1)))
bind = os.getenv("GUNICORN_BIND", "unix:/run/myfin/flask_app.sock")
threads = 2
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
loglevel = os.getenv("LOG_LEVEL", "info")
accesslog = "-"
errorlog = "-"

# Recommended for systemd socket path
umask = 0o007

# If behind a proxy, trust X-Forwarded-* headers
forwarded_allow_ips = "*"
proxy_protocol = False
