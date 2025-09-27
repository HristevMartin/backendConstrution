from flask_restful import Resource
from models.project_counter import JobApplicationCounter as JobCounterModel


class JobApplicationCounterResource(Resource):
    def get(self, job_id):
        job = JobCounterModel.objects(job_id=job_id).first()
        if not job:
            return {"error": "Job not found"}, 404
        return {"count": job.applied_count}
    
    def post(self, job_id):
        job = JobCounterModel.objects(job_id=job_id).first()
        if not job:
            job = JobCounterModel(job_id=job_id, applied_count=1).save()
        else:
            job.applied_count += 1
        job.applied_count += 1
        job.save()
        return {"count": job.applied_count}