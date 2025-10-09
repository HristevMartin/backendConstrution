from flask_restful import Resource
from managers.auth import auth
from models.TraderProject import TraderProject
from models.user import Users


class VerifiedTrader(Resource):
    @auth.login_required
    def get(self, user_id):
        
        trader_user_id = str(user_id)
        
        trader_project = Users.objects(id=trader_user_id).first()
        print('show me the trader_project', trader_project)

        if trader_project:
            trader_role = trader_project.role
            print('show me the trader_role', trader_role)
            if ("master" in trader_role):
                print('in heree eee', trader_role)
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