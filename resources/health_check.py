from flask_restful import Resource

class HealthCheck(Resource):
    def get(self):
        return {'message': 'Health check successful'}, 200