from flask_restful import Resource
from flask import request
from models.UserTracker import ClientUserCompletedJobs
from managers.auth import auth, _get_token_from_request


class GetClientCompletedJobs(Resource):
    def get(self, job_id):
        try:
            print('show me the job_id', job_id)
            client_completed_jobs = ClientUserCompletedJobs.objects(jobId=job_id)
            print('show me in here what is the client_completed_jobs', client_completed_jobs)
            
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
            
            # Count actual jobs by status
            total_completed = 0
            total_cancelled = 0
            total_jobs = user_jobs.count()  # Total number of job records
            
            for job in user_jobs:
                if job.completed_jobs > 0:
                    total_completed += 1
                if job.cancelled_jobs > 0:
                    total_cancelled += 1
            
            # In progress jobs = total jobs - completed jobs - cancelled jobs
            in_progress_jobs = total_jobs - total_completed - total_cancelled
            
            return {
                'success': True,
                'completed_jobs': total_completed,
                'in_progress_jobs': in_progress_jobs,
                'total_posted': total_jobs,
                'total_cancelled': total_cancelled,
                'message': 'Client job statistics retrieved successfully'
            }, 200
        except Exception as e:
            print('Error in GetClientCompletedJobs:', e)
            return {
                'success': False,
                'error': str(e),
                'message': 'Client completed jobs retrieval failed'
            }, 500


class GetAllClientStatusProjects(Resource):
    @auth.login_required
    def get(self):
        try:
            token = _get_token_from_request()
            if not token or token == 'null' or token == 'undefined' or token.strip() == '':
                return {"error": "Valid token is required. Token cannot be null, undefined, or empty."}, 401

            user_id = str(auth.current_user().id)
            user_jobs = ClientUserCompletedJobs.objects(userId=user_id)
            
            print('show me the user_completed_jobs count', user_jobs.count())
            
            # Count actual jobs by status
            total_completed = 0
            total_cancelled = 0
            total_jobs = user_jobs.count()  # Total number of job records
            
            for job in user_jobs:
                if job.completed_jobs > 0:
                    total_completed += 1
                if job.cancelled_jobs > 0:
                    total_cancelled += 1
            
            # In progress jobs = total jobs - completed jobs - cancelled jobs
            in_progress_jobs = total_jobs - total_completed - total_cancelled
            
            # Convert QuerySet to list of dictionaries
            projects_list = []
            for job in user_jobs:
                projects_list.append({
                    'id': job.id,
                    'jobId': job.jobId,
                    'completed_jobs': job.completed_jobs,
                    'cancelled_jobs': job.cancelled_jobs,
                    'posted_jobs': job.posted_jobs,
                    'last_completed_at': job.last_completed_at.isoformat() if job.last_completed_at else None,
                    'first_posted_at': job.first_posted_at.isoformat() if job.first_posted_at else None,
                    'response_rate': job.response_rate,
                    'reliable': job.reliable,
                    'created_at': job.created_at.isoformat() if job.created_at else None,
                    'updated_at': job.updated_at.isoformat() if job.updated_at else None
                })
            
            return {
                'success': True,
                'completed_jobs': total_completed,
                'in_progress_jobs': in_progress_jobs,
                'total_posted': total_jobs,
                'total_cancelled': total_cancelled,
                'projects': projects_list,
                'count': len(projects_list),
                'message': 'Client status projects retrieved successfully'
            }, 200
        except Exception as e:
            print('Error in GetAllClientStatusProjects:', e)
            return {
                'success': False,
                'error': str(e),
                'message': 'Client status projects retrieval failed'
            }, 500