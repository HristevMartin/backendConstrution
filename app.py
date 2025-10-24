from datetime import datetime, timedelta               
from flask import Flask, request, g  
from config import Config
from flask_cors import CORS
from flask_restful import Api
from managers.auth import AuthManager, COOKIE_NAME 
from flask_mongoengine import MongoEngine

from resources.routes import routes

db = MongoEngine()

# Refresh token if within 7 days of expiry (instead of 1 day)
ROLLING_WINDOW = timedelta(days=7)
# Cookie expires in 180 days (matches JWT expiry)
COOKIE_MAX_AGE = 180 * 24 * 60 * 60  # 180 days in seconds

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.secret_key = "dasdasdasdasdas!321312?"
    
    env_mode = "PRODUCTION" if Config.IS_PRODUCTION else "DEVELOPMENT"
    print(f"🚀 Starting backend in {env_mode} mode")
    
    # Log cookie settings on startup
    Config.log_cookie_settings()
    Config.validate_email_config()

    db.init_app(app)

    api = Api(app)

    [api.add_resource(*r) for r in routes]

    # CORS Configuration
    CORS(app, 
         origins=[
             "http://localhost:8000",              
             "http://localhost:3000",             
             "http://192.168.0.46:8000",          
             "http://192.168.0.37:8000",          
             "https://find-tradespeople.com",     
             "https://www.find-tradespeople.com"  
         ],
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
         expose_headers=['Set-Cookie'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'])

    @app.after_request
    def maybe_refresh_jwt(resp):
        try:
            if not request.path.startswith("/travel/"):
                return resp
            if request.path.endswith("/logout") or request.method == "OPTIONS":
                return resp

            payload = getattr(g, "jwt_payload", None)
            if not payload:
                return resp  

            exp_val = payload.get("exp")
            if not exp_val:
                return resp

            exp_dt = datetime.utcfromtimestamp(exp_val) if isinstance(exp_val, (int, float)) else exp_val
            time_until_expiry = exp_dt - datetime.utcnow()
            
            # Log for debugging in production
            if Config.IS_PRODUCTION:
                print(f"🕐 Token expires in: {time_until_expiry.days} days for user {payload.get('sub')}")
            
            if time_until_expiry <= ROLLING_WINDOW:
                new_token = AuthManager.encode_token(payload["sub"], payload.get("role"))
                
                # Use dynamic cookie configuration
                cookie_config = Config.get_cookie_config()
                
                cookie_params = {
                    "key": COOKIE_NAME,
                    "value": new_token,
                    "max_age": COOKIE_MAX_AGE,
                    **cookie_config  
                }
                
                resp.set_cookie(**cookie_params)
                print(f"🔄 Token refreshed for user: {payload.get('sub')} (was expiring in {time_until_expiry.days} days)")
                
        except Exception as e:
            print(f"⚠️ Error refreshing token: {str(e)}")
            import traceback
            traceback.print_exc()
        return resp

    return app


if not Config.IS_PRODUCTION:
    if __name__ == "__main__":
        app = create_app()
        app.run(host='0.0.0.0', port=8080, debug=True)