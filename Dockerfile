FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ libpq-dev python3-dev curl git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt gunicorn celery redis
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

# COPY start_celery.sh .
# RUN chmod +x start_celery.sh

EXPOSE 8080

# CMD ["./start_celery.sh"]
CMD ["gunicorn", "--bind", ":8080", "--workers", "2", "--threads", "4", "--timeout", "0", "--access-logfile", "-", "--error-logfile", "-", "app:create_app()"]