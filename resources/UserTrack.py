from flask_restful import Resource
from flask import request
from models.UserTrack import UserTrackDb


class UserTrack(Resource):
    def post(self):
        data = request.get_json()
        print('user track data is', data)
        UserTrackDb(**data).save()
        return {"message": "User track saved successfully"}, 200
