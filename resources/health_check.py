from flask_restful import Resource
from flask import request
from models.page_visit import PageVisit
import user_agents

class HealthCheck(Resource):
    def get(self):
        return {'message': 'Health check successful'}, 200


class SecondHealthCheck(Resource):
    def get(self):
        return {'message': 'Second heassltsh schesckss successsful'}, 200


class ThirdHealthCheck(Resource):
    def get(self):
        return {'message': 'Third heassltsh schesckss successsful'}, 200