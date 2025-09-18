import os
from datetime import datetime, timedelta

import jwt
from bson import ObjectId
from flask_httpauth import HTTPTokenAuth
from werkzeug.exceptions import BadRequest

from models.user import BlacklistedToken, Users

jwt_secret_key = os.getenv("SECRET_KEY")
jwt_secret_key = "dsadsadsadasdasdasdsadsa"

class AuthManager:
    @staticmethod
    def encode_token(user_id, role):
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(days=7),
            "role": role,
        }
        token = jwt.encode(payload, key=jwt_secret_key, algorithm="HS256")
        return token

    @staticmethod
    def decode_token(token):
        try:
            print(f"🔍 Attempting to decode token with secret key: {jwt_secret_key[:10]}...")
            data = jwt.decode(token, key=jwt_secret_key, algorithms=["HS256"])
            print(f"🔍 Decoded JWT payload: {data}")
            return data["sub"], data["role"]

        except jwt.ExpiredSignatureError:
            print("❌ JWT token has expired")
            raise BadRequest("Token expired")

        except jwt.InvalidTokenError as e:
            print(f"❌ Invalid JWT token: {str(e)}")
            raise BadRequest("Invalid token")


auth = HTTPTokenAuth(scheme="Bearer")


@auth.verify_token
def verify_token(token):
    print(f"🔑 Received token: {token[:50]}...")
    
    try:
        user_id, role = AuthManager.decode_token(token)
        print(f"🔑 Decoded user_id: {user_id}, role: {role}")
    except Exception as e:
        print(f"❌ Failed to decode token: {str(e)}")
        return None

    # if BlacklistedToken.objects(token=token).first():
    #     return None

    try:
        user = Users.objects(id=ObjectId(user_id)).first()
        print(f"👤 Found user: {user.email if user else 'None'}")
    except Exception as e:
        print(f"❌ Failed to fetch user from MongoDB: {str(e)}")
        return None

    return user
