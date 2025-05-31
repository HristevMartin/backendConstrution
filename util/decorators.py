from flask import request
from werkzeug.exceptions import BadRequest

from managers.auth import auth


def validate_schema(schema_name):
    def wrapper(func):
        def decorated_func(*args, **kwargs):
            data = request.get_json()
            schema = schema_name()
            errors = schema.validate(data)
            if errors:
                raise BadRequest(errors)
            return func(*args, **kwargs)

        return decorated_func

    return wrapper


def permission_required(*permissions):
    def wrapper(func):
        def decorated_function(*args, **kwargs):
            user = auth.current_user()
            required_permissions = {permission.value for permission in permissions}

            user_roles = (
                set(user["role"]) if isinstance(user["role"], list) else {user["role"]}
            )

            if not required_permissions.issubset(user_roles):
                return {"message": "You do not have access to this resource"}, 403
            return func(*args, **kwargs)

        return decorated_function

    return wrapper
