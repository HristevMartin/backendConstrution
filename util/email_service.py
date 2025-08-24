# util/email_service.py

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from datetime import datetime
from config import Config
import logging



class EmailService:
    def __init__(self):
        # Check if email is configured
        if not Config.SENDGRID_API_KEY:
            print("SendGrid API key not configured. Emails will not be sent.")
            self.enabled = False
            return
            
        self.enabled = True
        self.sg = SendGridAPIClient(api_key=Config.SENDGRID_API_KEY)
        self.from_email = Config.SENDGRID_FROM_EMAIL
        self.admin_email = "virtoala0@gmail.com"
        self.company_name = Config.COMPANY_NAME
        
    def send_project_confirmation_email(self, project_data):
        """
        Send confirmation email to client after project submission
        """
        if not self.enabled:
            print("📧 Email service disabled - confirmation email not sent")
            return False
            
        try:
            # Extract project information
            email = project_data.get('email')
            first_name = project_data.get('first_name', 'Client')
            project_id = project_data.get('project_id')
            project_id = project_id.split('-')[0]
            print('the project id is', project_id)
            job_title = project_data.get('job_title', 'Project')
            urgency = project_data.get('urgency', 'flexible')
            image_count = project_data.get('image_count', 0)
            created_at = project_data.get('created_at')
            
            # Format creation date
            if isinstance(created_at, str):
                try:
                    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    formatted_date = created_date.strftime('%B %d, %Y at %I:%M %p')
                except:
                    formatted_date = created_at
            else:
                formatted_date = datetime.now().strftime('%B %d, %Y at %I:%M %p')
            
            subject = f"✅ Project Submitted - {job_title}"
            
            # Simplified HTML email template (MVP)
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Project Submitted</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; }}
                    .header {{ background: #4CAF50; color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; }}
                    .project-details {{ background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                    .footer {{ background: #f5f5f5; padding: 15px; text-align: center; color: #666; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎉 Project Submitted!</h1>
                    </div>
                    
                    <div class="content">
                        <p>Hi {first_name},</p>
                        
                        <p>Your project <strong>"{job_title}"</strong> has been submitted successfully.</p>
                        
                        <div class="project-details">
                            <strong>Project ID:</strong> {project_id}<br>
                            <strong>Submitted:</strong> {formatted_date}<br>
                            <strong>Images:</strong> {image_count} photo(s)
                        </div>
                        
                        <p><strong>What happens next?</strong></p>
                        <p>Local tradespeople will be notified about your project and can contact you directly with quotes and availability.</p>
                        
                        <p>Questions? Reply to this email.</p>
                        
                        <p>Thanks for using {self.company_name}!</p>
                        
                        <p>— {self.company_name} Team</p>
                    </div>
                    
                    <div class="footer">
                        <p>Project #{project_id}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Simplified plain text version (MVP)
            text_content = f"""
            Hi {first_name},

            Your project "{job_title}" has been submitted successfully.

            Project ID: {project_id}
            Submitted: {formatted_date}
            Images: {image_count} photo(s)

            What happens next?
            Local tradespeople will be notified about your project and can contact you directly with quotes and availability.

            Questions? Reply to this email.

            Thanks for using {self.company_name}!

            — {self.company_name} Team

            Project #{project_id}
            """
            
            # Create and send the email
            message = Mail(
                from_email=self.from_email,
                to_emails=email,
                subject=subject,
                html_content=html_content,
                plain_text_content=text_content
            )
            
            response = self.sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                print(f"📧 Confirmation email sent successfully to {email}")
                return True
            else:
                print(f"Failed to send email. Status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error sending confirmation email: {str(e)}")
            return False

    def send_job_posted_email(self, job_data):
        """
        Send job posted confirmation email to client (MVP version)
        """
        if not self.enabled:
            print("📧 Email service disabled - job posted email not sent")
            return False
            
        try:
            # Extract job information
            email = job_data.get('email') or job_data.get('clientEmail')
            first_name = job_data.get('firstName') or job_data.get('first_name', 'Client')
            job_title = job_data.get('jobTitle') or job_data.get('job_title', 'Your Project')
            city = job_data.get('city', 'your area')
            view_job_url = job_data.get('viewJobUrl', '#')
            brand_name = job_data.get('brandName', self.company_name)
            
            subject = f'Your job is live: "{job_title}"'
            
            # Simple, clean HTML template for MVP
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Job Posted Successfully</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; }}
                    .header {{ background: #4CAF50; color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; }}
                    .cta-button {{ 
                        display: inline-block; 
                        background: #007cba; 
                        color: white; 
                        padding: 12px 30px; 
                        text-decoration: none; 
                        border-radius: 5px; 
                        margin: 20px 0;
                        font-weight: bold;
                    }}
                    .footer {{ background: #f5f5f5; padding: 20px; text-align: center; color: #666; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎉 Your job is live!</h1>
                    </div>
                    
                    <div class="content">
                        <p>Hi {first_name},</p>
                        
                        <p>Your job <strong>"{job_title}"</strong> has been posted in <strong>{city}</strong>.</p>
                        
                        <p>Local tradespeople will be notified and can apply shortly.</p>
                        
                        <div style="text-align: center;">
                            <a href="{view_job_url}" class="cta-button">View your job</a>
                        </div>
                        
                        <p>Thanks for using {brand_name}!</p>
                        
                        <p>— {brand_name} Team</p>
                    </div>
                    
                    <div class="footer">
                        <p>This email was sent to {email} regarding your job posting.</p>
                        <p>&copy; 2025 {brand_name}. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text version (MVP)
            text_content = f"""
            Hi {first_name},

            Your job "{job_title}" has been posted in {city}.
            Local tradespeople will be notified and can apply shortly.

            View your job: {view_job_url}

            Thanks for using {brand_name}!

            — {brand_name} Team
            """
            
            # Create and send the email
            message = Mail(
                from_email=self.from_email,
                to_emails=email,
                subject=subject,
                html_content=html_content,
                plain_text_content=text_content
            )
            
            response = self.sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                print(f"📧 Job posted email sent successfully to {email}")
                return True
            else:
                print(f"Failed to send job posted email. Status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error sending job posted email: {str(e)}")
            return False
    
    def send_admin_notification_email(self, project_data):
        """
        Send notification email to admin/team about new project submission
        """
        if not self.enabled:
            print("📧 Email service disabled - admin notification not sent")
            return False
            
        try:
            # Extract project information
            client_email = project_data.get('email')
            first_name = project_data.get('first_name', 'Client')
            project_id = project_data.get('project_id')
            job_title = project_data.get('job_title', 'Project')
            job_description = project_data.get('job_description', 'N/A')
            urgency = project_data.get('urgency', 'flexible')
            image_count = project_data.get('image_count', 0)
            phone = project_data.get('phone', 'Not provided')
            
            subject = f"🚨 New Project Submission - {job_title}"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #ff6b6b; color: white; padding: 20px; text-align: center; }}
                    .content {{ background: #f9f9f9; padding: 20px; }}
                    .urgent {{ background: #ffebee; border-left: 4px solid #f44336; padding: 15px; margin: 10px 0; }}
                    .project-info {{ background: white; padding: 15px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>🚨 New Project Submission</h2>
                    </div>
                    <div class="content">
                        {f'<div class="urgent"><strong>⚡ URGENT PROJECT</strong> - Client marked as {urgency.upper()}</div>' if urgency == 'asap' else ''}
                        
                        <div class="project-info">
                            <h3>Client Information</h3>
                            <p><strong>Name:</strong> {first_name}</p>
                            <p><strong>Email:</strong> {client_email}</p>
                            <p><strong>Phone:</strong> {phone}</p>
                            
                            <h3>Project Details</h3>
                            <p><strong>Project ID:</strong> {project_id}</p>
                            <p><strong>Title:</strong> {job_title}</p>
                            <p><strong>Description:</strong> {job_description}</p>
                            <p><strong>Urgency:</strong> {urgency.title()}</p>
                            <p><strong>Images:</strong> {image_count} photo(s)</p>
                        </div>
                        
                        <p><strong>Action Required:</strong> Review project and contact client within 24-48 hours.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            message = Mail(
                from_email=self.from_email,
                to_emails=self.admin_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                print(f" Admin notification sent successfully to {self.admin_email}")
                return True
            else:
                print(f"Failed to send admin notification. Status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f" Error sending admin notification: {str(e)}")
            return False