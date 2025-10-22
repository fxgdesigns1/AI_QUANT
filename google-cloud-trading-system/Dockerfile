FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Debug: List files to verify accounts.yaml is copied
RUN ls -la /app/ | head -20
RUN ls -la /app/accounts.yaml || echo "accounts.yaml not found"

# Create data directory
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PORT=8080

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/api/analytics/health || exit 1

# Run the application
CMD ["python3", "cloud_main.py"]
