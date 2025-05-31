from flask_restful import Resource
from models.user import Users
from bson.objectid import ObjectId
import json

class GetUser(Resource):
    def get(self, user_id):
        print('show me the user id', user_id)
        user_id_mongo = ObjectId(user_id)
        user = Users.objects(id=user_id_mongo).first()
        print('show me the fetched user', user)
        user_data = user.email.split('@')[0]
        print('show me the user data', user_data)
        if user:
            res = {"message": "User found", "user": user_data}
            return res, 200
        else:
            return {"message": "User not found"}, 404

