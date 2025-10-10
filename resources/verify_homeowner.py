from flask_restful import Resource
from models.ClientProject import ClientProject
from models.user import Users



class CheckVerifiedHomeowner(Resource):
    def get(self, job_id):
        job_id = ClientProject.objects(project_id=job_id).first()
        print('show me the job_id', job_id)
        
        homeowner_id = job_id.user_id
        print('show me the homeowner_id', homeowner_id)
        homeowner = Users.objects(id=homeowner_id).first()
        print('show me the homeowner', homeowner)
        if homeowner:
            homeowner_role = homeowner.role
            print('show me the homeowner_role', homeowner_role)
            if "verifiedOwner" in homeowner_role:
                return {'message': 'Homeowner is verified', 'status': True}, 200
            else:
                return {'message': 'Homeowner is not verified', 'status': False}, 404
        else:
            return {'message': 'Homeowner not found', 'status': False}, 404