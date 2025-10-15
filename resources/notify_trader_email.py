from flask_restful import Resource
from flask import request
from util.email_service import EmailService
from config import Config
from typing import Optional

email_service = EmailService()

def fmt_km(distance) -> Optional[str]:
    try:
        d = float(distance)
        if d > 0:
            return f"{d:.1f} km"
    except (TypeError, ValueError):
        pass
    return None

class NotifyTraderByEmailFromChat(Resource):
    def post(self):
        """
        Send job notification email to trader from AI chat
        Expected payload:
        {
            "trader": {"traderId", "name", "email", "trade", "city", "postcode", ...},
            "job": {"jobId", "title", "location", "serviceCategory"},
            "homeowner": {"id", "name"}
        }
        """
        try:
            data = request.get_json()
            print('[NotifyTraderByEmail] Received data:', data)
            
            # Extract data
            trader = data.get('trader', {})
            job = data.get('job', {})
            homeowner = data.get('homeowner', {})
            
            # Validate required fields
            if not trader.get('email'):
                return {'ok': False, 'error': 'Trader email is required'}, 400
            
            if not job.get('jobId'):
                return {'ok': False, 'error': 'Job ID is required'}, 400
            
            # Prepare email data
            email_data = {
                'trader_name': trader.get('name', 'Trader'),
                'trader_email': trader.get('email'),
                'job_id': job.get('jobId'),
                'job_title': job.get('title', 'New Job Opportunity'),
                'job_location': job.get('location', 'Location not specified'),
                'job_category': job.get('serviceCategory', 'General'),
                'homeowner_name': homeowner.get('name', 'Homeowner'),
                'trader_trade': trader.get('trade', ''),
                'trader_city': trader.get('city', ''),
                'distance': trader.get('distanceKm', 0)
            }
            
            # Send email
            success = send_trader_job_notification(email_data)
            
            if success is True:
                print(f'[NotifyTraderByEmail] ✅ Email sent to {trader.get("email")} for job {job.get("jobId")}')
                return {
                    'ok': True, 
                    'message': f'Notification sent to {trader.get("name")}',
                    'trader': trader.get('name'),
                    'email': trader.get('email')
                }, 200
            elif success is False:
                print(f'[NotifyTraderByEmail] ❌ Email disabled for job {job.get("jobId")}')
                return {
                    'ok': False, 
                    'error': 'Email service disabled'
                }, 503
            else:
                print(f'[NotifyTraderByEmail] ❌ Failed to send email for job {job.get("jobId")}')
                return {
                    'ok': False, 
                    'error': 'Failed to send email notification'
                }, 502
                    
        except Exception as e:
            print(f'[NotifyTraderByEmail] Error: {e}')
            return {'ok': False, 'error': str(e)}, 500


def send_trader_job_notification(email_data):
    if not email_service.enabled:
        print(f"Email service disabled - job {email_data.get('job_id', 'N/A')} not sent")
        return False
    
    try:
        trader_name = email_data.get('trader_name', 'Trader')
        trader_email = email_data.get('trader_email')
        job_title = email_data.get('job_title', 'New Job')
        job_location = email_data.get('job_location', 'Location')
        job_category = email_data.get('job_category', 'General')
        job_id = email_data.get('job_id', 'N/A')
        distance = email_data.get('distance')
        budget = email_data.get('budget')
        
        job_url = f"{Config.FRONTEND_BASE_URL}/jobs/{job_id}?utm_source=email&utm_medium=notify&utm_campaign=trader_alert"
        
        dist_str = fmt_km(distance)
        opt_dist = f" ({dist_str})" if dist_str else ""
        
        subject = f"New {job_category} job near {job_location} – {job_title}{opt_dist}"
        
        distance_line = f"<div class=\"detail\">Distance: <strong>{dist_str}</strong></div>" if dist_str else ""
        
        budget_value = None
        if budget:
            try:
                budget_value = float(str(budget).replace('£','').replace(',','').strip())
            except (ValueError, TypeError):
                pass
        budget_line = f"<div class=\"detail\">Budget: <strong>£{budget_value:,.0f}</strong></div>" if budget_value else ""
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style type="text/css">
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0; background: #f5f5f5; }}
.wrapper {{ max-width: 580px; margin: 20px auto; background: #ffffff; border-radius: 6px; overflow: hidden; }}
.content {{ padding: 32px 28px; }}
.greeting {{ font-size: 16px; margin: 0 0 16px 0; color: #111; }}
.job-box {{ background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 4px; padding: 20px; margin: 20px 0; }}
.detail {{ font-size: 14px; margin: 8px 0; color: #374151; }}
.cta {{ text-align: center; margin: 24px 0; }}
.btn {{ display: inline-block; background: #2563eb; color: #ffffff !important; padding: 12px 32px; text-decoration: none; border-radius: 5px; font-weight: 600; }}
.footer {{ background: #111827; color: #9ca3af; padding: 20px 28px; font-size: 12px; text-align: center; }}
.footer a {{ color: #60a5fa; text-decoration: none; }}
</style>
<span style="display:none !important; visibility:hidden; mso-hide:all; font-size:1px; color:#ffffff; line-height:1px; max-height:0px; max-width:0px; opacity:0; overflow:hidden;">View details & apply</span>
</head>
<body>
<div class="wrapper">
<div class="content">
<p class="greeting">Hi {trader_name},</p>
<p style="margin: 0 0 16px 0; font-size: 14px; color: #374151;">A new {job_category} job matches your area and skills.</p>
<div class="job-box">
<div class="detail">Job: <strong>{job_title}</strong></div>
<div class="detail">Trade: <strong>{job_category}</strong></div>
<div class="detail">Location: <strong>{job_location}</strong></div>
{distance_line}
{budget_line}
</div>
<div class="cta">
<a href="{job_url}" class="btn">View &amp; Apply</a>
</div>
</div>
<div class="footer">
Job Hub &nbsp;|&nbsp; <a href="{Config.FRONTEND_BASE_URL}/notifications">Manage notifications</a> &nbsp;|&nbsp; <a href="mailto:{email_service.from_email}">Support</a>
</div>
</div>
</body>
</html>"""
        
        dist_txt = f"\nDistance: {dist_str}" if dist_str else ""
        budget_txt = f"\nBudget: £{budget_value:,.0f}" if budget_value else ""
        
        text_content = f"""Hi {trader_name},

A new {job_category} job matches your area and skills.

Job: {job_title}
Trade: {job_category}
Location: {job_location}{dist_txt}{budget_txt}

View & Apply:
{job_url}

Job Hub
Manage notifications: {Config.FRONTEND_BASE_URL}/notifications
Support: {email_service.from_email}
"""
        
        from sendgrid.helpers.mail import Mail
        
        message = Mail(
            from_email=email_service.from_email,
            to_emails=trader_email,
            subject=subject,
            html_content=html_content,
            plain_text_content=text_content
        )
        
        response = email_service.sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            print(f"Trader job notification sent to {trader_email} for job {job_id}")
            return True
        else:
            print(f"Failed to send job {job_id}. Status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error sending job {email_data.get('job_id', 'N/A')}: {str(e)}")
        return None
