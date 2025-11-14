# resources/celery_test.py
from flask import jsonify
from flask_restful import Resource
from flask import request
from models.TraderProject import TraderProject
from tasks import simple_log_task
from celery_app import celery

class CeleryTestResource(Resource):
    def get(self):
        res = {'id': 'None', 'project_id': '39a58507-dff1-4ca5-ab31-814f00ab4a14', 'user_id': '68e28af2e2d9a864b1c27442', 'first_name': 'Ivan', 'email': 'virtoala0@gmail.com', 'phone': '07703294186', 'contact_method': 'email', 'job_title': 'Testds', 'job_description': 'dsajdsadasd asdasdsa', 'location': 'London', 'postcode': 'SW20 9NP', 'nuts': 'Merton', 'budget': 'Custom: £400', 'urgency': 'this_week', 'country': 'GB', 'service_category': '', 'image_urls': [], 'image_count': 0, 'created_at': '2025-11-14T09:40:21.153547', 'updated_at': '2025-11-14T09:40:21.153547', 'status': 'pending', 'gdpr_consent': True, 'additional_data': {'country': 'GB', 'postcode': 'SW20 9NP', 'area': 'London', 'location': 'London', 'serviceCategory': 'Electrical', 'jobTitle': 'Testds', 'jobDescription': 'dsajdsadasd asdasdsa', 'budget': 'Custom: £400', 'budgetType': 'custom', 'budgetAmount': '400', 'customBudget': '400', 'urgency': 'this_week', 'firstName': 'Ivan', 'email': 'virtoala0@gmail.com', 'phone': '07703294186', 'gdprConsent': 'true', 'userId': '68e28af2e2d9a864b1c27442', 'project_id': '39a58507-dff1-4ca5-ab31-814f00ab4a14', 'user_id': '68e28af2e2d9a864b1c27442', 'created_at': '2025-11-14T09:40:21.044143', 'image_urls': [], 'nuts': 'Merton'}}

        result = simple_log_task.delay(res)
        
        # print(f'Task queued with ID: {result.id}, Message: {res}')
        return {
            'message': 'Background task has been queued!',
            'task_id': "result.id",
            'status': "result.state", 
            'queued_message': "message", 
            'note': 'This response returned immediately, task runs in background',
            'check_status_url': f'/travel/celery-test/status/{"result.id"}'
        }, 200
    

