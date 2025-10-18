# FROM python:3.11-slim

# WORKDIR /app

# # Install system-level build dependencies including git
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     gcc \
#     g++ \
#     libpq-dev \
#     python3-dev \
#     curl \
#     git \
#     && rm -rf /var/lib/apt/lists/*

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

# CMD ["python", "app.py"]

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

# Cloud Run uses $PORT (defaults to 8080 locally)
ENV PORT=8080

# Start with Gunicorn
CMD ["gunicorn", "--bind", ":$PORT", "app:create_app()"]
