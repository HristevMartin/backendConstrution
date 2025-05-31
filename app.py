from config import Config
from flask import Flask
from flask_cors import CORS
from flask_restful import Api
# from flask_restx import Api
from flask_mongoengine import MongoEngine

from models.passenger import initialize_passenger_types
from resources.routes import routes

db = MongoEngine()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    api = Api(app)

    # api = Api(app, version='1.0', title='API Documentation',
    #           description='A detailed description of the API')

    [api.add_resource(*r) for r in routes]

    initialize_passenger_types()

    CORS(app, origins=["*"], allow_headers=["Authorization", "Content-Type"])

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=8080)

