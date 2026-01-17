# Gunicorn configuration for load testing
import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout
timeout = 30
keepalive = 10

# Logging
loglevel = 'info'
accesslog = '-'
errorlog = '-'

# Process naming
proc_name = 'tmdt_load_test'

# Server mechanics
preload_app = True
pidfile = '/tmp/gunicorn.pid'
user = None
group = None
tmp_upload_dir = None

# Performance
worker_tmp_dir = '/dev/shm' if os.path.exists('/dev/shm') else None
