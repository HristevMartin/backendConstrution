from flask_restful import Resource
from flask import request
from models.user import Users
from bson.objectid import ObjectId
from managers.auth import auth, _get_token_from_request
import json
from models.TraderProject import TraderProject

class GetUser(Resource):
    def get(self, user_id):
        user_id_mongo = ObjectId(user_id)
        user = Users.objects(id=user_id_mongo).first()
        user_data = user.email.split('@')[0]
        if user:
            res = {"message": "User found", "user": user_data}
            return res, 200
        else:
            return {"message": "User not found"}, 404
        

class SaveUserRole(Resource):
    def post(self):
        try:
            data = request.get_json()
            print('Received role data:', data)
            
            # Validate required fields
            if not data.get('userId'):
                return {"error": "User ID is required"}, 400
            
            if not data.get('rolePreference'):
                return {"error": "Role preference is required"}, 400
            
            user_id = data['userId']
            role_preference = data['rolePreference']
            
            print(f'Saving role preference "{role_preference}" for user: {user_id}')
            
            # Find user by ObjectId
            try:
                user_id_mongo = ObjectId(user_id)
                user = Users.objects(id=user_id_mongo).first()
            except:
                return {"error": "Invalid user ID format"}, 400
            
            if not user:
                return {"error": "User not found"}, 404
            
            # Update user's role preference
            # If role is a single value, store it as a list
            if isinstance(role_preference, str):
                user.role = [role_preference]
            elif isinstance(role_preference, list):
                user.role = role_preference
            else:
                user.role = [str(role_preference)]
            
            # Save the user
            user.save()
            
            print(f'Role preference saved successfully for user {user.email}: {user.role}')
            
            return {
                "message": "User role saved successfully",
                "userId": str(user.id),
                "email": user.email,
                "rolePreference": user.role
            }, 200
            
        except Exception as e:
            print(f"Error saving user role: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to save user role: {str(e)}"}, 500


class GetUserRole(Resource):
    def get(self):
        user_id = request.args.get('userId')
        user_id_mongo = ObjectId(user_id)
        user = Users.objects(id=user_id_mongo).first()
        return user.role, 200


class GetUserData(Resource):
    @auth.login_required
    def get(self):
        token = _get_token_from_request()
        user_id = auth.current_user().id
        
        if not token or token == 'null' or token == 'undefined' or token.strip() == '':
            return {"error": "Valid token is required. Token cannot be null, undefined, or empty."}, 401

        user_id_mongo = ObjectId(user_id)
        user = Users.objects(id=user_id_mongo).first()
        print('show me the user in here', user.id)
        print('show me the user_id type', type(user_id))
        trader_projec = TraderProject.objects(userId=str(user_id)).first()

    
        print('show me the trader project in here', trader_projec.postcode)

        return  trader_projec.postcode, 200
