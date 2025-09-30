import os
from datetime import datetime, timedelta

import jwt
from bson import ObjectId
from flask_httpauth import HTTPTokenAuth
from werkzeug.exceptions import BadRequest
from flask import request, g

from models.user import BlacklistedToken, Users

jwt_secret_key = os.getenv("SECRET_KEY")
jwt_secret_key = "dsadsadsadasdasdasdsadsa"
JWT_ALGS   = ["HS256"]
COOKIE_NAME = "access_token"

class AuthManager:
    @staticmethod
    def encode_token(user_id, role):
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(days=60),
            "role": role,
            "iat": datetime.utcnow(), 
        }
        token = jwt.encode(payload, key=jwt_secret_key, algorithm="HS256")
        return token

    @staticmethod
    def decode_token_with_payload(token):
        try:
            data = jwt.decode(token, key=jwt_secret_key, algorithms=["HS256"])
            return data["sub"], data.get("role"), data
        except jwt.ExpiredSignatureError:
            raise BadRequest("Token expired")
        except jwt.InvalidTokenError as e:
            raise BadRequest("Invalid token")


auth = HTTPTokenAuth(scheme="Bearer")

def _get_token_from_request() -> str | None:
    tok = request.cookies.get(COOKIE_NAME)
    if tok:
        return tok

    authz = request.headers.get("Authorization", "")
    if authz.lower().startswith("bearer "):
        return authz.split(" ", 1)[1].strip()
    return None


@auth.verify_token
def verify_token(token):
    token = _get_token_from_request()
    if not token:
        return None
    print(f"🔑 Received token: {token[:50]}...")
    
    try:
        user_id, role, payload = AuthManager.decode_token_with_payload(token)
        g.jwt_payload = payload 
        print(f"🔑 Decoded user_id: {user_id}, role: {role}")
    except Exception as e:
        print(f"❌ Failed to decode token: {str(e)}")
        return None

    try:
        user = Users.objects(id=ObjectId(user_id)).first()
        print(f"👤 Found user: {user.email if user else 'None'}")
    except Exception as e:
        print(f"❌ Failed to fetch user from MongoDB: {str(e)}")
        return None

    return user
