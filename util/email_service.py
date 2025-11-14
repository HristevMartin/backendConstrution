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
        self.admin_email = Config.ADMIN_EMAIL
        self.company_name = Config.COMPANY_NAME
        
    def test_sendgrid_connection(self):
        """Test SendGrid connection with a simple API call"""
        if not self.enabled:
            print("📧 Email service disabled - cannot test connection")
            return False
            
        try:
            # Try to get account information to test the API key
            response = self.sg.client.user.get()
            print(f"✅ SendGrid connection successful! Status: {response.status_code}")
            return True
        except Exception as e:
            print(f"❌ SendGrid connection failed: {str(e)}")
            return False
        
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
                print(f"Response body: {response.body}")
                print(f"Response headers: {response.headers}")
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
                print(f"Response body: {response.body}")
                print(f"Response headers: {response.headers}")
                return False
                
        except Exception as e:
            print(f" Error sending admin notification: {str(e)}")
            return False

    def send_trader_registration_email(self, trader_data):
        """
        Send confirmation email to trader after registration
        """
        if not self.enabled:
            print("📧 Email service disabled - trader registration email not sent")
            return False
            
        try:
            # Extract trader information
            email = trader_data.get('email')
            name = trader_data.get('name', 'Trader')
            primary_trade = trader_data.get('primaryTrade', 'Trade')
            city = trader_data.get('city', 'Location')
            project_id = trader_data.get('project_id', 'N/A')
            
            subject = f"🎉 Welcome to Job Hub - Registration Confirmed!"
            
            # HTML email template for trader registration with Job Hub branding
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Welcome to Job Hub - Registration Confirmed</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                    .logo {{ font-size: 32px; font-weight: bold; margin-bottom: 10px; }}
                    .tagline {{ font-size: 16px; opacity: 0.9; }}
                    .content {{ padding: 30px; }}
                    .welcome-message {{ background: #f8f9ff; padding: 25px; border-radius: 12px; margin: 20px 0; border-left: 4px solid #667eea; }}
                    .trader-details {{ background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                    .next-steps {{ background: #e8f4fd; padding: 25px; border-radius: 12px; margin: 20px 0; border-left: 4px solid #2196F3; }}
                    .trust-badges {{ background: #f0f8f0; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; }}
                    .footer {{ background: #2c3e50; color: white; padding: 20px; text-align: center; font-size: 14px; }}
                    .cta-button {{ 
                        display: inline-block; 
                        background: #667eea; 
                        color: white; 
                        padding: 12px 30px; 
                        text-decoration: none; 
                        border-radius: 25px; 
                        margin: 20px 0;
                        font-weight: bold;
                        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">🏠 Job Hub</div>
                        <div class="tagline">Connecting skilled professionals with homeowners</div>
                    </div>
                    
                    <div class="content">
                        <div class="welcome-message">
                            <h2>Hi {name}! 👋</h2>
                            <p><strong>We're excited to have you onboard!</strong></p>
                            <p>Homeowners in <strong>{city}</strong> and surrounding areas are waiting for skilled professionals like you. Your expertise in <strong>{primary_trade}</strong> is exactly what they need.</p>
                        </div>
                        
                        <p>Your trader registration has been confirmed successfully! 🎉</p>
                        
                        <div class="trader-details">
                            <h3>📋 Registration Summary</h3>
                            <p><strong>Name:</strong> {name}</p>
                            <p><strong>Primary Trade:</strong> {primary_trade}</p>
                            <p><strong>Location:</strong> {city}</p>
                            <p><strong>Registration ID:</strong> {project_id}</p>
                        </div>
                        
                        <div class="next-steps">
                            <h3>🚀 What happens next?</h3>
                            <p><strong>1. Profile Review (24-48 hours):</strong> Our team will review your registration to ensure quality standards.</p>
                            <p><strong>2. Account Activation:</strong> You'll receive an email once your account is activated.</p>
                            <p><strong>3. Start Receiving Jobs:</strong> Once activated, you'll start receiving job notifications in your area and can begin earning!</p>
                        </div>
                        
                        <div class="trust-badges">
                            <h4>🔒 Trust & Safety</h4>
                            <p>All tradespeople on Job Hub are verified & insured for your peace of mind.</p>
                        </div>
                        
                        <p><strong>Need help?</strong> Reply to this email or contact our support team - we're here to help you succeed!</p>
                        
                        <p>Welcome to the Job Hub family! 🏠✨</p>
                        
                        <p>— The Job Hub Team</p>
                    </div>
                    
                    <div class="footer">
                        <p>This email was sent to {email}</p>
                        <p><strong>Job Hub</strong> - Connecting skilled professionals with homeowners</p>
                        <p>&copy; {datetime.now().year} Job Hub. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text version
            text_content = f"""
            🏠 Welcome to Job Hub!
            
            Hi {name}!
            
            We're excited to have you onboard! Homeowners in {city} and surrounding areas are waiting for skilled professionals like you. Your expertise in {primary_trade} is exactly what they need.
            
            Your trader registration has been confirmed successfully! 🎉
            
            Registration Summary:
            - Name: {name}
            - Primary Trade: {primary_trade}
            - Location: {city}
            - Registration ID: {project_id}
            
            What happens next?
            1. Profile Review (24-48 hours): Our team will review your registration to ensure quality standards.
            2. Account Activation: You'll receive an email once your account is activated.
            3. Start Receiving Jobs: Once activated, you'll start receiving job notifications in your area and can begin earning!
            
            Trust & Safety: All tradespeople on Job Hub are verified & insured for your peace of mind.
            
            Need help? Reply to this email or contact our support team - we're here to help you succeed!
            
            Welcome to the Job Hub family! 🏠✨
            
            — The Job Hub Team
            
            Job Hub - Connecting skilled professionals with homeowners
            """
            
            message = Mail(
                from_email=self.from_email,
                to_emails=email,
                subject=subject,
                html_content=html_content,
                plain_text_content=text_content
            )
            
            response = self.sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                print(f"📧 Trader registration email sent successfully to {email}")
                return True
            else:
                print(f"Failed to send trader registration email. Status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error sending trader registration email: {str(e)}")
            return False

    def send_trader_admin_notification_email(self, trader_data):
        """
        Send notification email to admin about new trader registration
        """
        if not self.enabled:
            print("📧 Email service disabled - trader admin notification not sent")
            return False
            
        try:
            # Extract trader information
            name = trader_data.get('name', 'Trader')
            email = trader_data.get('email', 'N/A')
            phone = trader_data.get('phone', 'Not provided')
            primary_trade = trader_data.get('primaryTrade', 'N/A')
            city = trader_data.get('city', 'N/A')
            postcode = trader_data.get('postcode', 'N/A')
            radius_km = trader_data.get('radiusKm', 'N/A')
            experience_years = trader_data.get('experienceYears', 'N/A')
            certifications = trader_data.get('certifications', 'None')
            bio = trader_data.get('bio', 'No bio provided')
            marketing_consent = trader_data.get('marketingConsent', 'false')
            project_id = trader_data.get('project_id', 'N/A')
            
            subject = f"🆕 New Trader Registration - {name} ({primary_trade})"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }}
                    .logo {{ font-size: 28px; font-weight: bold; margin-bottom: 10px; }}
                    .tagline {{ font-size: 14px; opacity: 0.9; }}
                    .content {{ background: #f9f9f9; padding: 20px; }}
                    .trader-info {{ background: white; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #667eea; }}
                    .contact-info {{ background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #4CAF50; }}
                    .action-required {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #ffc107; }}
                    .footer {{ background: #2c3e50; color: white; padding: 15px; text-align: center; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">🏠 Job Hub</div>
                        <div class="tagline">New Trader Registration Alert</div>
                    </div>
                    <div class="content">
                        <div class="trader-info">
                            <h3>👷 Trader Information</h3>
                            <p><strong>Name:</strong> {name}</p>
                            <p><strong>Primary Trade:</strong> {primary_trade}</p>
                            <p><strong>Location:</strong> {city}, {postcode}</p>
                            <p><strong>Service Radius:</strong> {radius_km} km</p>
                            <p><strong>Experience:</strong> {experience_years} years</p>
                            <p><strong>Certifications:</strong> {certifications}</p>
                            <p><strong>Bio:</strong> {bio}</p>
                            <p><strong>Marketing Consent:</strong> {marketing_consent}</p>
                            <p><strong>Registration ID:</strong> {project_id}</p>
                        </div>
                        
                        <div class="contact-info">
                            <h3>📞 Contact Information</h3>
                            <p><strong>Email:</strong> {email}</p>
                            <p><strong>Phone:</strong> {phone}</p>
                        </div>
                        
                        <div class="action-required">
                            <h3>⚡ Action Required</h3>
                            <p><strong>Review trader profile and activate account within 24-48 hours.</strong></p>
                            <p>This helps maintain quality standards and ensures timely service for homeowners.</p>
                        </div>
                    </div>
                    <div class="footer">
                        <p><strong>Job Hub</strong> - Connecting skilled professionals with homeowners</p>
                        <p>&copy; {datetime.now().year} Job Hub. All rights reserved.</p>
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
                print(f"📧 Trader admin notification sent successfully to {self.admin_email}")
                return True
            else:
                print(f"Failed to send trader admin notification. Status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"📧 Error sending trader admin notification: {str(e)}")
            return False
            

    def send_trader_new_project_email(self, trader_emails, template_data):
        """
        Send 'new project posted' notification to a list of traders.
        `template_data` is what prepare_template_and_data(message) returns.
        """
        if not self.enabled:
            print("📧 Email service disabled - trader new project emails not sent")
            return False

        subject = template_data["subject"]
        text_body = template_data["text_body"]
        html_body = template_data["html_body"]

        try:
            for email in trader_emails:
                message = Mail(
                    from_email=self.from_email,
                    to_emails=email,
                    subject=subject,
                    html_content=html_body,
                    plain_text_content=text_body,
                )
                response = self.sg.send(message)

                if response.status_code not in [200, 201, 202]:
                    print(f"Failed to send trader new project email to {email}. "
                          f"Status: {response.status_code}")

            print(f"Trader new project emails sent successfully to {trader_emails}")
            return True
        except Exception as e:
            print(f"Error sending trader new project emails: {str(e)}")
            return False