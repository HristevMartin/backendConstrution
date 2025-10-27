from flask_restful import Resource
from flask import request
from managers.auth import auth
from models.user import Users

class HomeOwnerVerification(Resource):
    @auth.login_required
    def post(self):
        user_id = str(auth.current_user().id)
        
        user = Users.objects(id=user_id).first()
        print('show me the user', user)
        
        if not user:
            return {'message': 'User not found', 'status': False}, 404
        
        # Ensure role is a list
        if not isinstance(user.role, list):
            user.role = [user.role] if user.role else []
        
        user.role.append("wantedVerifiedOwner")
        user.save()
        return {
            'message': 'Homeowner verified successfully',
            'status': True,
            'roles': user.role
        }, 200