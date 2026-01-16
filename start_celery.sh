#!/bin/bash
set -e

echo "============================================"
echo " Starting JobHub Backend Services"
echo "============================================"

echo " Environment: ${FLASK_ENV:-production}"
echo "  MongoDB: ${DB_HOST}:${DB_PORT}/${MONGO_DB}"
echo " Redis: ${REDIS_URL}"

echo ""
echo " Starting Celery worker..."
celery -A celery_app.celery worker \
    --loglevel=info \
    --pool=solo \
    --concurrency=2 &

CELERY_PID=$!
echo "✓ Celery worker started (PID: $CELERY_PID)"

sleep 2

echo ""
echo " Starting Flask API with Gunicorn..."
exec gunicorn \
    --bind :8080 \
    --workers 2 \
    --threads 4 \
    --timeout 0 \
    --access-logfile - \
    --error-logfile - \
    "app:create_app()"