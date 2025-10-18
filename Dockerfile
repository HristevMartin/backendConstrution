FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ libpq-dev python3-dev curl git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy project files
COPY . .

# Expose port (documentation only)
EXPOSE 8080

# Start with Gunicorn - use shell form to expand $PORT
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60 "app:create_app()"