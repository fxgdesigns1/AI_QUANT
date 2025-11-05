# Dashboard (Advanced) - Cloud Run container
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# System deps
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements first for better caching
COPY dashboard/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy repo
COPY . /app

# Cloud Run expects the app to listen on $PORT
ENV PORT=${PORT}

# Use Gunicorn with eventlet worker for Flask-SocketIO
# Note: background updater is started via @app.before_first_request
CMD ["bash", "-lc", "exec gunicorn -k eventlet -w 1 -b 0.0.0.0:$PORT dashboard.advanced_dashboard:app"]
