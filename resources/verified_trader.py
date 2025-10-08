from flask_restful import Resource
from managers.auth import auth
from models.TraderProject import TraderProject


class VerifiedTrader(Resource):
    @auth.login_required
    def get(self, user_id):
        user_id = str(auth.current_user().id)
        print('show me the user_id', user_id)
        trader_project = TraderProject.objects(userId=user_id).first()
        if trader_project:
            trader_role = trader_project.role
            if ("master" in trader_role):
                return {
                    "success": True,
                    "message": "Trader is a master"
                }, 200
            else:
                return {
                    "success": False,
                    "message": "Trader is not a master"
                }, 404
        else:
            return {
                "success": False,
                "message": "Trader project not found"
            }, 404