import secrets
import hashlib
from datetime import datetime, timedelta

from flask import request, jsonify
from flask_restful import Resource
from werkzeug.security import generate_password_hash, check_password_hash

from managers.auth import auth, AuthManager
from managers.user import User
from models.enums import RoleType
from models.user import Users, BlacklistedToken
from schemas.requests.user import TravelRegisterRequestSchema, TravelLoginRequestSchema
from util.decorators import validate_schema, permission_required
from util.send_reset_password import _send_reset_email
from config import Config

# Constants for password reset
APP_BASE_URL = Config.APP_BASE_URL
RESET_TTL_MIN = 30  # Reset token expires in 30 minutes

def _sha256(text: str) -> str:
    """Create SHA256 hash of text"""
    return hashlib.sha256(text.encode()).hexdigest()


class Register(Resource):
    # @validate_schema(TravelRegisterRequestSchema)
    def post(self):
        print('in here')
        result = User().check_and_create_user_data(request)
        print('blqblqblq', result)
        if 'message' in result:
            return result, 400
        else:
            # Create and save the new user
            new_user = Users(**result)
            new_user.save()
            print('new_user', new_user)
            # Generate token for automatic login
            user_id = str(new_user.id)
            user_role = result["role"][0] if result["role"] else 'USER'
            token = AuthManager.encode_token(user_id, user_role)
            
            # Get language from request for callback URL
            lang = request.json.get("lang", "en")
            
            # Return login data for automatic login
            return {
                "id": user_id,
                "role": user_role,
                "token": token
            }, 201


class Login(Resource):
    # @validate_schema(TravelLoginRequestSchema)
    def post(self):
        result, status = User().authenticate_user(request)
        print('show me the result', result)
        # If login was successful, transform response to match registration format
        if status == 200 and 'access_token' in result:
            
            # Transform response to match registration format
            return {
                "id": result.get("user_id"),
                "role": result.get("role"),
                "token": result.get("access_token")
            }, 200
        
        # Return error response as is
        return result, status


class UpdateUserRole(Resource):
    @auth.login_required
    @permission_required(RoleType.ADMIN)
    def patch(self, user_id):
        new_role = request.json.get("new_role")
        action = request.json.get("action")

        if not new_role:
            return {"error": "Missing role"}, 400

        if action == "add":
            res = User.add_role_to_user(user_id, new_role)
            return res
        elif action == "remove":
            res = User.remove_role_from_user(user_id, new_role)
            return res
        else:
            return {"error": "Invalid action specified"}, 400


class InsertAdminUser(Resource):
    def get(self):
        admin_user = Users(
            email="admin@gmail.com",
            password=generate_password_hash("root", method="pbkdf2:sha256"),
            createdAt=datetime.utcnow(),
            isDeleted=False,
            role=[RoleType.ADMIN.value]
        )

        admin_user.save()

        return {"message": "Admin user created successfully"}, 201

    def post(self):
        data = request.get_json()

        existing_user = Users.objects(email=data["email"]).first()

        if existing_user:
            return {"message": "An agent with this email already exists"}, 400

        agent_user = Users(
            email=data["email"],
            password=generate_password_hash(data["password"], method="pbkdf2:sha256"),
            createdAt=datetime.utcnow(),
            isDeleted=False,
            role=[RoleType.AGENT.value]
        )

        agent_user.save()

        return {"message": "Agent user created successfully"}, 201


class Logout(Resource):
    @auth.login_required
    def delete(self):
        current_user = auth.current_user()

        if not current_user:
            return {"message": "Invalid user session"}, 401

        token = request.headers.get("Authorization").split(" ")[1]
        expires_at = datetime.utcnow() + timedelta(days=1)

        try:
            BlacklistedToken(
                token=token,
                expiresAt=expires_at,
                reason="User logged out",
                userId=current_user["id"],
                email=current_user["email"],
                role=current_user["role"]
            ).save()

            return {"message": "Logged out successfully"}, 200
        except Exception as e:
            print("Failed to blacklist token:", str(e))
            return {"message": "Failed to logout"}, 500


class Test(Resource):
    # @auth.login_required
    # @permission_required(RoleType.MANAGEMENT, RoleType.ADMIN)
    def get(self):
        return {"message": "Hello World!"}


class ForgotPassword(Resource):
    # POST /travel/forgot-password  { "email": "user@example.com" }
    def post(self):
        data  = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()

        # Always return 200 (avoid user enumeration)
        user = Users.objects(email=email).first()
        if user:
            raw = secrets.token_urlsafe(32)
            user.reset_token_hash = _sha256(raw)
            user.reset_expires_at = datetime.utcnow() + timedelta(minutes=RESET_TTL_MIN)
            user.reset_used_at    = None
            user.save()

            reset_link = f"{APP_BASE_URL}/reset-password?token={raw}"
            print(f"show me the reset link", reset_link)
            _send_reset_email(email, reset_link)

        return {"success": True, "message": "If that email exists, we’ve sent a reset link."}, 200


class ResetPassword(Resource):
    # POST /travel/reset-password  { "token": "reset_token", "new_password": "new_password" }
    def post(self):
        data = request.get_json() or {}
        token = data.get("token", "").strip()
        new_password = data.get("new_password", "").strip()
        
        if not token or not new_password:
            return {"error": "Token and new password are required"}, 400
        
        if len(new_password) < 6:
            return {"error": "Password must be at least 6 characters long"}, 400
        
        token_hash = _sha256(token)
        user = Users.objects(reset_token_hash=token_hash).first()
        
        if not user:
            return {"error": "Invalid or expired reset token"}, 400
        
        # Check if token is expired
        if user.reset_expires_at and user.reset_expires_at < datetime.utcnow():
            return {"error": "Reset token has expired"}, 400
        
        # Check if token was already used
        if user.reset_used_at:
            return {"error": "Reset token has already been used"}, 400
        
        # Update user password and mark token as used
        user.password = generate_password_hash(new_password, method="pbkdf2:sha256")
        user.reset_used_at = datetime.utcnow()
        user.reset_token_hash = None  # Clear the token
        user.reset_expires_at = None
        user.save()
        
        return {"success": True, "message": "Password has been reset successfully"}, 200
