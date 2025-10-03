from flask_restful import Resource
from flask import request
from models.UserTracker import ClientUserCompletedJobs
from managers.auth import auth


class GetClientCompletedJobs(Resource):
    def get(self, job_id):
        try:
            print('show me the job_id', job_id)
            client_completed_jobs = ClientUserCompletedJobs.objects(jobId=job_id)
            
            # Get the first job to find the user_id
            first_job = client_completed_jobs.first()
            if not first_job:
                return {
                    'success': True,
                    'completed_jobs': 0,
                    'in_progress_jobs': 0,
                    'message': 'No jobs found for this job_id'
                }, 200
            
            user_id = first_job.userId
            user_jobs = ClientUserCompletedJobs.objects(userId=user_id)

            print('show me the user_completed_jobs count', user_jobs.count())
            
            # Calculate totals
            total_completed = 0
            total_posted = 0
            
            for job in user_jobs:
                total_completed += job.completed_jobs
                total_posted += job.posted_jobs
            
            # In progress jobs = posted jobs - completed jobs
            in_progress_jobs = total_posted - total_completed
            
            return {
                'success': True,
                'completed_jobs': total_completed,
                'in_progress_jobs': in_progress_jobs,
                'total_posted': total_posted,
                'message': 'Client job statistics retrieved successfully'
            }, 200
        except Exception as e:
            print('Error in GetClientCompletedJobs:', e)
            return {
                'success': False,
                'error': str(e),
                'message': 'Client completed jobs retrieval failed'
            }, 500