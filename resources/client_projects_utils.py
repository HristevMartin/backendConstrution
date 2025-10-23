from flask_restful import Resource
from models.application import Application

class CheckIfAnyJobIsPaid(Resource):
    def get(self, job_id):
        print('aaaaaaaaaaaaaaaaaaaaaaaa', job_id)
        try:
            application = Application.objects(job_id=job_id, status="paid").first()
            if application:
                return {"status": True}, 200
            else:
                return {"status": False}, 200
        except Exception as e:
            return {"status": False, "message": str(e)}, 500