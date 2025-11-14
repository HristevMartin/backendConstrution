# tasks.py (in root directory, same level as app.py)
from celery_app import celery
import time
from datetime import datetime
from models.TraderProject import TraderProject
from mongoengine import Q
from services.notify_traders import get_traders_emails_by_service_category
from services.notify_traders import prepare_template_and_data
from util.email_service import EmailService

@celery.task(name='tasks.simple_log_task')
def simple_log_task(message):
    """
    Super simple task - just logs a message
    """
    try:
        searched_service_category = message.get('additional_data', {}).get('serviceCategory', '')

        trader_emails = get_traders_emails_by_service_category(searched_service_category)
        print('show me the trader emails', trader_emails)
        
        template_data = prepare_template_and_data(message)
        email_service = EmailService()
        email_service.send_trader_new_project_email(trader_emails, template_data)

        return {
            "sent_to": trader_emails,
            "subject": template_data["subject"],
        }
        
    except Exception as e:
        print(f"Error in simple_log_task: {str(e)}")
        return False