from datetime import datetime, timedelta               
from flask import Flask, request, g  
from config import Config
from flask_cors import CORS
from flask_restful import Api
from managers.auth import AuthManager, COOKIE_NAME 
from flask_mongoengine import MongoEngine

from models.passenger import initialize_passenger_types
from resources.routes import routes

db = MongoEngine()

ROLLING_WINDOW = timedelta(hours=24)        
COOKIE_MAX_AGE = 60 * 24 * 60 * 60

# Cookie settings based on environment
COOKIE_SECURE = Config.IS_PRODUCTION
COOKIE_SAMESITE = "None" if Config.IS_PRODUCTION else "Lax"  

# LOCAL development origins
FRONTEND_ORIGIN = [
    "http://localhost:8000",     
    "http://192.168.0.46:8000",
    "http://192.168.0.37:8000"    
]

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.secret_key = "dasdasdasdasdas!321312?"
    
    # Log environment mode
    env_mode = "PRODUCTION" if Config.IS_PRODUCTION else "DEVELOPMENT"
    print(f"🚀 Starting backend in {env_mode} mode")
    print(f"   Cookie settings: secure={COOKIE_SECURE}, samesite={COOKIE_SAMESITE}")

    db.init_app(app)

    api = Api(app)

    # api = Api(app, version='1.0', title='API Documentation',
    #           description='A detailed description of the API')

    [api.add_resource(*r) for r in routes]

    initialize_passenger_types()

    # CORS Configuration
    # PRODUCTION: Use production domain(s) only
    # LOCAL: Use local IPs and localhost
    CORS(app, 
         origins=[
             "http://localhost:8000",              # LOCAL
             "http://192.168.0.46:8000",          # LOCAL
             "http://192.168.0.37:8000",          # LOCAL
             "https://find-tradespeople.com"      # PRODUCTION
         ],
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

    @app.after_request
    def maybe_refresh_jwt(resp):
        try:
            # Only act on your API, skip logout & preflights
            if not request.path.startswith("/travel/"):
                return resp
            if request.path.endswith("/logout") or request.method == "OPTIONS":
                return resp

            payload = getattr(g, "jwt_payload", None)
            if not payload:
                return resp  # unauthenticated or decode failed (401 path)

            exp_val = payload.get("exp")
            if not exp_val:
                return resp

            # exp can be a timestamp (int/float) or datetime
            exp_dt = datetime.utcfromtimestamp(exp_val) if isinstance(exp_val, (int, float)) else exp_val
            if (exp_dt - datetime.utcnow()) <= ROLLING_WINDOW:
                new_token = AuthManager.encode_token(payload["sub"], payload.get("role"))
                resp.set_cookie(
                    COOKIE_NAME,
                    new_token,
                    max_age=COOKIE_MAX_AGE,
                    httponly=True,
                    secure=COOKIE_SECURE,
                    samesite=COOKIE_SAMESITE,
                    path="/",
                )
        except Exception:
            pass
        return resp

    return app


# if __name__ == "__main__":
#     app = create_app()
#     app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

