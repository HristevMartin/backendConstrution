from flask_restful import Resource
from flask import request
from util.email_service import EmailService
from config import Config

# Initialize email service
email_service = EmailService()

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
            
            if success:
                print(f'[NotifyTraderByEmail] ✅ Email sent successfully to {trader.get("email")}')
                return {
                    'ok': True, 
                    'message': f'Notification sent to {trader.get("name")}',
                    'trader': trader.get('name'),
                    'email': trader.get('email')
                }, 200
            else:
                print(f'[NotifyTraderByEmail] ❌ Failed to send email')
                return {
                    'ok': False, 
                    'error': 'Failed to send email notification'
                }, 500
                    
        except Exception as e:
            print(f'[NotifyTraderByEmail] Error: {e}')
            return {'ok': False, 'error': str(e)}, 500


def send_trader_job_notification(email_data):
    """Send job opportunity notification to trader"""
    if not email_service.enabled:
        print("📧 Email service disabled - trader job notification not sent")
        return False
    
    try:
        trader_name = email_data.get('trader_name', 'Trader')
        trader_email = email_data.get('trader_email')
        job_title = email_data.get('job_title', 'New Job')
        job_location = email_data.get('job_location', 'Location')
        job_category = email_data.get('job_category', 'General')
        homeowner_name = email_data.get('homeowner_name', 'Homeowner')
        job_id = email_data.get('job_id', 'N/A')
        distance = email_data.get('distance', 0)
        
        # Build the job application URL
        job_url = f"{Config.FRONTEND_BASE_URL}/jobs/{job_id}"
        
        subject = f"🔔 New {job_category} Job in {job_location} - Apply Now!"
        
        # Professional HTML email template for traders
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>New Job Opportunity - {job_category}</title>
            <style>
                body {{ font-family: Arial, Helvetica, sans-serif; line-height: 1.6; color: #000000; margin: 0; padding: 0; background-color: #f4f6f8; }}
                .email-wrapper {{ background-color: #f4f6f8; padding: 20px 0; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: #ffffff; padding: 40px 30px; text-align: center; }}
                .header-badge {{ background: rgba(255,255,255,0.3); display: inline-block; padding: 8px 16px; border-radius: 20px; font-size: 14px; font-weight: 600; margin-bottom: 10px; color: #ffffff; }}
                .logo {{ font-size: 28px; font-weight: 700; margin: 10px 0 5px 0; color: #ffffff; }}
                .tagline {{ font-size: 16px; margin: 0; color: #ffffff; }}
                .content {{ padding: 35px 30px; }}
                .greeting {{ font-size: 24px; font-weight: 700; color: #000000; margin: 0 0 20px 0; }}
                .intro {{ font-size: 16px; color: #000000; margin-bottom: 25px; font-weight: 400; }}
                .job-card {{ background: #e0f2fe; border-left: 4px solid #3b82f6; padding: 25px; border-radius: 8px; margin: 25px 0; }}
                .job-card h3 {{ color: #000000; margin: 0 0 20px 0; font-size: 18px; font-weight: 700; }}
                .job-detail {{ display: flex; align-items: center; margin: 12px 0; font-size: 15px; }}
                .job-detail-label {{ font-weight: 700; color: #000000; min-width: 90px; }}
                .job-detail-value {{ color: #000000; font-weight: 400; }}
                .highlight-box {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 20px; border-radius: 8px; margin: 25px 0; }}
                .highlight-box strong {{ color: #000000; font-weight: 700; }}
                .cta-section {{ text-align: center; margin: 35px 0; padding: 30px 20px; background: #f8fafc; border-radius: 8px; }}
                .cta-button {{ 
                    display: inline-block; 
                    background: #2563eb; 
                    color: #ffffff !important; 
                    padding: 16px 40px; 
                    text-decoration: none; 
                    border-radius: 8px; 
                    margin: 15px 0;
                    font-weight: 700;
                    font-size: 16px;
                    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
                }}
                .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 25px 0; }}
                .info-item {{ background: #e0f2fe; padding: 15px; border-radius: 6px; text-align: center; border: 1px solid #3b82f6; }}
                .info-item-value {{ font-size: 24px; font-weight: 700; color: #000000; }}
                .info-item-label {{ font-size: 14px; color: #000000; margin-top: 5px; font-weight: 400; }}
                .steps {{ background: #ffffff; border: 2px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 25px 0; }}
                .step {{ display: flex; align-items: start; margin: 15px 0; }}
                .step-number {{ background: #3b82f6; color: #ffffff; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; margin-right: 15px; flex-shrink: 0; font-size: 14px; }}
                .step-text {{ color: #000000; flex: 1; font-weight: 400; }}
                .footer {{ background: #1e293b; color: #ffffff; padding: 25px 30px; text-align: center; font-size: 13px; }}
                .footer-link {{ color: #60a5fa; text-decoration: none; font-weight: 400; }}
                .job-ref {{ background: rgba(255,255,255,0.2); display: inline-block; padding: 6px 12px; border-radius: 4px; margin-top: 10px; color: #ffffff; font-weight: 600; }}
                @media only screen and (max-width: 600px) {{
                    .info-grid {{ grid-template-columns: 1fr; }}
                }}
            </style>
        </head>
        <body>
            <div class="email-wrapper">
                <div class="container">
                    <div class="header">
                        <div class="header-badge">🎯 MATCHED TO YOUR SKILLS</div>
                        <div class="logo">🏠 Job Hub</div>
                        <p class="tagline">New Job Opportunity in Your Area</p>
                    </div>
                    
                    <div class="content">
                        <h1 class="greeting">Hi {trader_name}! 👋</h1>
                        
                        <p class="intro">A homeowner near you needs a <strong>{job_category}</strong> professional. This job matches your skills and location perfectly!</p>
                        
                        <div class="job-card">
                            <h3>📋 Job Details</h3>
                            
                            <div class="job-detail">
                                <span class="job-detail-label">Job Title:</span>
                                <span class="job-detail-value"><strong>{job_title}</strong></span>
                            </div>
                            
                            <div class="job-detail">
                                <span class="job-detail-label">Category:</span>
                                <span class="job-detail-value">{job_category}</span>
                            </div>
                            
                            <div class="job-detail">
                                <span class="job-detail-label">Location:</span>
                                <span class="job-detail-value">{job_location}</span>
                            </div>
                            
                            <div class="job-detail">
                                <span class="job-detail-label">Posted By:</span>
                                <span class="job-detail-value">{homeowner_name}</span>
                            </div>
                        </div>
                        
                        <div class="info-grid">
                            <div class="info-item">
                                <div class="info-item-value">{distance} km</div>
                                <div class="info-item-label">Distance from you</div>
                            </div>
                            <div class="info-item">
                                <div class="info-item-value">💰 TBD</div>
                                <div class="info-item-label">Budget (Discuss with client)</div>
                            </div>
                        </div>
                        
                        <div class="highlight-box">
                            <strong>🎯 Why You Were Selected:</strong><br>
                            ✓ Your skills match the job requirements<br>
                            ✓ You're located nearby ({distance} km away)<br>
                            ✓ You're an active, verified professional on our platform
                        </div>
                        
                        <div class="cta-section">
                            <p style="margin: 0 0 15px 0; font-size: 18px; font-weight: 700; color: #000000;">Ready to apply?</p>
                            <p style="margin: 0 0 20px 0; color: #000000; font-weight: 400;">View full job details and submit your application</p>
                            <a href="{job_url}" class="cta-button">
                                🔗 View & Apply for Job
                            </a>
                            <p style="margin: 20px 0 0 0; font-size: 13px; color: #000000; font-weight: 400;">Click the button above to access the job page</p>
                        </div>
                        
                        <div class="steps">
                            <h4 style="margin: 0 0 20px 0; color: #000000; font-weight: 700;">📝 How to Apply:</h4>
                            
                            <div class="step">
                                <div class="step-number">1</div>
                                <div class="step-text"><strong style="color: #000000; font-weight: 700;">Click the button above</strong> <span style="color: #000000; font-weight: 400;">to view the full job details</span></div>
                            </div>
                            
                            <div class="step">
                                <div class="step-number">2</div>
                                <div class="step-text"><strong style="color: #000000; font-weight: 700;">Review the requirements</strong> <span style="color: #000000; font-weight: 400;">and make sure it's a good fit</span></div>
                            </div>
                            
                            <div class="step">
                                <div class="step-number">3</div>
                                <div class="step-text"><strong style="color: #000000; font-weight: 700;">Submit your application</strong> <span style="color: #000000; font-weight: 400;">with your quote and availability</span></div>
                            </div>
                            
                            <div class="step">
                                <div class="step-number">4</div>
                                <div class="step-text"><strong style="color: #000000; font-weight: 700;">Get hired!</strong> <span style="color: #000000; font-weight: 400;">We'll connect you directly with the homeowner</span></div>
                            </div>
                        </div>
                        
                        <p style="color: #000000; font-size: 14px; margin-top: 30px; font-weight: 400;">
                            <strong style="font-weight: 700;">Need help?</strong> Reply to this email or contact our support team. We're here to help you win more jobs!
                        </p>
                        
                        <p style="margin-top: 25px; color: #000000; font-weight: 400;">
                            Best of luck with your application!<br>
                            <strong style="font-weight: 700;">— The Job Hub Team 🏠</strong>
                        </p>
                    </div>
                    
                    <div class="footer">
                        <p style="margin: 0 0 5px 0; color: #ffffff; font-weight: 400;">This opportunity was sent to <strong style="font-weight: 700;">{trader_email}</strong></p>
                        <div class="job-ref">Job ID: #{job_id[:12]}</div>
                        <p style="margin: 15px 0 0 0; color: #ffffff; font-weight: 400;">
                            <strong style="font-weight: 700;">Job Hub</strong> - Connecting skilled tradespeople with homeowners<br>
                            &copy; 2025 Job Hub. All rights reserved.
                        </p>
                        <p style="margin: 15px 0 0 0; color: #ffffff;">
                            <a href="{job_url}" style="color: #60a5fa; text-decoration: none; font-weight: 600;">View Job</a> • 
                            <a href="mailto:{email_service.from_email}" style="color: #60a5fa; text-decoration: none; font-weight: 600;">Contact Support</a>
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
🏠 JOB HUB - NEW JOB OPPORTUNITY
🎯 MATCHED TO YOUR SKILLS

Hi {trader_name}!

A homeowner near you needs a {job_category} professional. This job matches your skills and location perfectly!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 JOB DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Job Title: {job_title}
Category: {job_category}
Location: {job_location}
Posted By: {homeowner_name}

Distance: {distance} km from you
Budget: TBD (Discuss with client)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 WHY YOU WERE SELECTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Your skills match the job requirements
✓ You're located nearby ({distance} km away)
✓ You're an active, verified professional on our platform

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 APPLY FOR THIS JOB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Click or copy this link to view full details and apply:
{job_url}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 HOW TO APPLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Click the link above to view the full job details
2. Review the requirements and make sure it's a good fit
3. Submit your application with your quote and availability
4. Get hired! We'll connect you directly with the homeowner

Need help? Reply to this email or contact our support team. 
We're here to help you win more jobs!

Best of luck with your application!
— The Job Hub Team 🏠

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This opportunity was sent to {trader_email}
Job ID: #{job_id[:12]}

Job Hub - Connecting skilled tradespeople with homeowners
© 2025 Job Hub. All rights reserved.

View Job: {job_url}
Contact Support: {email_service.from_email}
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
            print(f"📧 Trader job notification sent successfully to {trader_email}")
            return True
        else:
            print(f"Failed to send trader job notification. Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error sending trader job notification: {str(e)}")
        return False
