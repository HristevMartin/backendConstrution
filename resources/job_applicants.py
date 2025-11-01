from flask_restful import Resource
from models.application import Application

class GetApplicantsPerJob(Resource):
    def get(self, job_id):
        try:
            applicants = Application.objects(job_id=job_id).count()
            print('show me the applicants', applicants)
            return {"count": applicants}, 200
        except Exception as e:
            return {"error": str(e)}, 500