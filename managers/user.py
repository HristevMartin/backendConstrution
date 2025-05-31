from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from managers.auth import AuthManager
from models.enums import RoleType
from models.user import Users


class User:

    @staticmethod
    def check_and_create_user_data(request):
        email = request.json.get("email")
        password = request.json.get("password")
        repeat_password = request.json.get("password2")
        role = request.json.get("role", RoleType.NEW_USER.value)

        if not email or not password:
            return {"message": "Missing email or password", "status": 400}

        if password != repeat_password:
            return {"message": "Passwords do not match", "status": 400}

        existing_user = Users.objects(email=email).first()
        if existing_user:
            return {"message": "User already exists", "status": 409}

        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        return {
            "email": email,
            "password": hashed_password,
            "createdAt": datetime.now(),
            "isDeleted": False,
            "role": [role]
        }

    @staticmethod
    def authenticate_user(request):
        email = request.json.get("email")
        password = request.json.get("password")

        if not email or not password:
            return {"message": "Missing email or password"}, 400

        login_user = Users.objects(email=email).first()
        if login_user and check_password_hash(login_user.password, password):
            user_id = str(login_user.id)
            user_role = getattr(login_user, 'role', 'user')
            token = AuthManager.encode_token(user_id, user_role)
            return {"access_token": token, "user_id": user_id, "role": user_role, 'customerId': login_user.customerId}, 200

        return {"message": "Wrong password or user not found"}, 401

    @staticmethod
    def add_role_to_user(user_id, new_role):
        if new_role not in [role.value for role in RoleType]:
            return {"message": "Invalid role"}, 400

        user = Users.objects(id=user_id).first()
        if not user:
            return {"message": "User not found"}, 404

        if new_role not in user.role:
            user.update(push__role=new_role)
            return {"message": "Role added successfully"}, 200
        else:
            return {"message": "Role already exists"}, 409

    @staticmethod
    def remove_role_from_user(user_id, role):
        if role not in [role.value for role in RoleType]:
            return {"message": "Invalid role"}, 400

        user = Users.objects(id=user_id).first()
        if not user:
            return {"message": "User not found"}, 404

        if role in user.role:
            user.update(pull__role=role)
            return {"message": "Role removed successfully"}, 200
        else:
            return {"message": "Role not found"}, 404
