import secrets
import hashlib
from datetime import datetime, timedelta

from flask import request, jsonify, make_response
from flask_restful import Resource
from werkzeug.security import generate_password_hash, check_password_hash

from managers.auth import auth, AuthManager
from managers.user import User
from models.enums import RoleType
from models.user import Users
from schemas.requests.user import TravelRegisterRequestSchema, TravelLoginRequestSchema
from util.decorators import validate_schema, permission_required
from util.send_reset_password import _send_reset_email
from util.email_service import EmailService
from config import Config
from managers.auth import _get_token_from_request
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Constants for password reset
APP_BASE_URL = Config.APP_BASE_URL
RESET_TTL_MIN = 30  

COOKIE_NAME = "access_token"
# Cookie expires in 180 dayss (matches JWT expiry in managers/auth.py)
COOKIE_MAX_AGE = 180 * 24 * 60 * 60  # 180 days in seconds

def _sha256(text: str) -> str:
    """Create SHA256 hash of text"""
    return hashlib.sha256(text.encode()).hexdigest()


class Register(Resource):
    def post(self):
        result = User().check_and_create_user_data(request)

        if 'status' in result:
            status_code = result.pop('status')  
            return {"message": result.get('message')}, status_code

        # Create and persist user
        new_user = Users(**result)
        new_user.save()

        user_id = str(new_user.id)

        if isinstance(new_user.role, list):
            user_role = new_user.role[0] if new_user.role else 'USER'
        else:
            user_role = new_user.role or 'USER'

        token = AuthManager.encode_token(user_id, user_role)

        resp = make_response(jsonify({
            "id": user_id,
            "role": user_role
        }), 201)

        # Use dynamic cookie configuration
        cookie_config = Config.get_cookie_config()

        cookie_params = {
            "key": COOKIE_NAME,
            "value": token,
            "max_age": COOKIE_MAX_AGE,
            **cookie_config
        }

        resp.set_cookie(**cookie_params)
        print(f"🍪 Setting cookie in Register - domain: {Config.COOKIE_DOMAIN}, secure: {Config.COOKIE_SECURE}, samesite: {Config.COOKIE_SAMESITE}")
        return resp


class Login(Resource):
    def post(self):
        result, status = User().authenticate_user(request)
        if status == 200 and 'access_token' in result:

            token = result['access_token']

            body = {
                "id": result.get("user_id"),
                "role": result.get("role")
            }
            
            resp = make_response(jsonify(body), 200)

            # Use dynamic cookie configuration
            cookie_config = Config.get_cookie_config()

            cookie_params = {
                "key": COOKIE_NAME,
                "value": token,
                "max_age": COOKIE_MAX_AGE,
                **cookie_config
            }

            resp.set_cookie(**cookie_params)
            print(f"🍪 Setting cookie in Login:")
            print(f"   Domain: {Config.COOKIE_DOMAIN}")
            print(f"   Secure: {Config.COOKIE_SECURE}")
            print(f"   SameSite: {Config.COOKIE_SAMESITE}")
            print(f"   HttpOnly: {Config.COOKIE_HTTPONLY}")
            print(f"   Max-Age: {COOKIE_MAX_AGE} seconds ({COOKIE_MAX_AGE / 86400} days)")
            print(f"   Token (first 50 chars): {token[:50]}...")

            return resp
        
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
            user = auth.current_user()
            if not user:
                return {"message": "Invalid user session"}, 401

            # Optiosnal: read token for logging/metrics
            token = _get_token_from_request()

            resp = make_response(jsonify({"message": "Logged out successfully"}), 200)
            
            # Use dynamicc cookie configuration
            cookie_config = Config.get_cookie_config()

            cookie_params = {
                "key": COOKIE_NAME,
                "value": "",
                "max_age": 0,
                **cookie_config
            }

            resp.set_cookie(**cookie_params)
            return resp


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

class GetSession(Resource):
    @auth.login_required
    def get(self):
        try:
            from flask import g
            from datetime import datetime
            
            user = auth.current_user()
            if not user:
                return {"authenticated": False}, 401
            
            # Get JWT payload for expiry info
            payload = getattr(g, "jwt_payload", None)
            token_info = {}
            
            if payload:
                exp_val = payload.get("exp")
                if exp_val:
                    exp_dt = datetime.utcfromtimestamp(exp_val) if isinstance(exp_val, (int, float)) else exp_val
                    time_until_expiry = exp_dt - datetime.utcnow()
                    token_info = {
                        "expiresAt": exp_dt.isoformat(),
                        "daysUntilExpiry": time_until_expiry.days,
                        "hoursUntilExpiry": time_until_expiry.seconds // 3600
                    }
            
            response = {
                "authenticated": True,
                "id": str(user.id),
                "email": user.email,
                "role": user.role
            }
            
            # Include token info if available
            if token_info:
                response["tokenInfo"] = token_info
            
            return response, 200
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"authenticated": False, "error": "Failed to get session"}, 500



class GoogleAuth(Resource):
    def post(self):
        try:
            google_token = request.json.get('credential')
            role_from_request = request.json.get('role')
            
            idinfo = id_token.verify_oauth2_token(
                google_token, 
                google_requests.Request(), 
                Config.GOOGLE_CLIENT_ID
            )
            
            email = idinfo['email']
            google_id = idinfo['sub']
            name = idinfo.get('name', '')
            email_verified = idinfo.get('email_verified', False)
            
            existing_user = Users.objects(email=email).first()
            
            if existing_user:
                if existing_user.auth_provider == 'email':
                    return {
                        "message": "This email is registered with a password. Please sign in using your email and password above."
                    }, 400
                
                user_id = str(existing_user.id)
                user_role = existing_user.role[0] if isinstance(existing_user.role, list) else existing_user.role
                
            else:
                if not role_from_request:
                    return {
                        "message": "You don't have an account yet. Please register first:\n• Homeowners: Click 'Post a Job'\n• Tradespeople: Click 'Join as a Tradesperson'"
                    }, 400
                
                new_user = Users(
                    email=email,
                    google_id=google_id,
                    name=name,
                    email_verified=email_verified,
                    auth_provider='google',
                    role=[role_from_request]
                )
                new_user.save()
                
                user_id = str(new_user.id)
                user_role = role_from_request
            
            token = AuthManager.encode_token(user_id, user_role)
            
            resp = make_response(jsonify({
                "id": user_id,
                "role": user_role
            }), 200)
            
            cookie_config = Config.get_cookie_config()
            cookie_params = {
                "key": COOKIE_NAME,
                "value": token,
                "max_age": COOKIE_MAX_AGE,
                **cookie_config
            }
            
            resp.set_cookie(**cookie_params)
            return resp
            
        except ValueError as e:
            return {"message": "Invalid Google token"}, 401
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"message": str(e)}, 500