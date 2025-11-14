# Travel UB Application

## Overview
This is a API for management of travel service data. 

### Environment Variables
To set environment variables on Windows use the following commands:
```cmd
set MONGO_HOST=localhost
set MONGO_PORT=27017
set MONGO_DB=travelDB
set SECRET_KEY=very_secret_token
```

To set environment variables on Linux use the following commands:
```bash
export MONGO_HOST=localhost
export MONGO_PORT=27017
export MONGO_DB=travelDB
set SECRET_KEY=very_secret_token
set STRIPE_SECRET_KEY=sample
set OPENAI_API_KEY=sample
set SENDGRID_API_KEY=sample
set FLASK_ENV=dev
```

## Setup and Installation
1. Clone the repository: `git clone -b Release1 https://bitbucket.org/ubiquedigitalltd/ub-travel-services.git`
2. Install the required packages: `pip install -r requirements.txt`
3. Run the application: `python app.py`

### Locally use the following step to start the mongoDB container(prerequisite is to have docker-compose and docker installed locally):
4. Run MongoDB in a container: `docker-compose up -d`


### Start celery worker
celery -A celery_app.celery worker --loglevel=info --pool=solo