from models.TraderProject import TraderProject
from mongoengine import Q
from typing import Dict, Any
import os


def get_traders_emails_by_service_category(category):
    if not category:
        return []

    trader_emails = []

    if category:
        trader_projects = TraderProject.objects(
            Q(primaryTrade=category) | 
            Q(otherServices__contains=f'"{category}"')
        )

        for trader in trader_projects:
            trader_emails.append(trader.email)

    return trader_emails


def prepare_template_and_data(message: Dict[str, Any]) -> Dict[str, Any]:
    additional = message.get("additional_data", {})

    service_category = additional.get("serviceCategory")
    job_title = additional.get("jobTitle") or message.get("job_title", "New Job")
    job_description = additional.get("jobDescription")
    budget = additional.get("customBudget")
    postcode = additional.get("postcode")
    urgency_raw = additional.get("urgency", "")
    first_name = additional.get("firstName") or message.get("first_name")
    project_id = message.get("project_id")
    
    # Format urgency - replace underscores with spaces and capitalize
    urgency = urgency_raw.replace("_", " ").title() if urgency_raw else "Not specified"
    
    # Construct the project URL properly
    frontend_url = os.getenv("FRONTEND_BASE_URL", "https://find-tradespeople.com")
    project_url = f"{frontend_url}/jobs/{project_id}"

    context = {
        "service_category": service_category,
        "job_title": job_title,
        "job_description": job_description,
        "budget": budget,
        "postcode": postcode,
        "urgency": urgency,
        "first_name": first_name,
        "project_url": project_url,
    }

    subject = f"New {service_category} job in {postcode}"

    text_body = f"""
A new {service_category} job has been posted in {postcode}.

Job: {job_title}
Description: {job_description}
Budget: £{budget}
Urgency: {urgency}

View job and respond: {project_url}

You are receiving this notification because your profile matches the homeowner's requested service.

© Ivan — JobHub Marketplace
""".strip()

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>New Job Notification</title>
</head>

<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; 
             background-color: #f5f5f5; 
             margin: 0; 
             padding: 0;">
  
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f5f5f5; padding: 40px 0;">
    <tr>
      <td align="center">

        <!-- Main Card -->
        <table width="600" cellpadding="0" cellspacing="0" border="0" 
               style="background: #ffffff; 
                      border-radius: 8px; 
                      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                      max-width: 600px;">

          <!-- Logo Header -->
          <tr>
            <td style="padding: 30px 40px 20px 40px; border-bottom: 1px solid #e8eaed;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <div style="display: inline-flex; align-items: center;">
                      <!-- JobHub Icon (using emoji/text for now) -->
                      <div style="background: linear-gradient(135deg, #1a73e8 0%, #4285f4 100%);
                                  width: 40px;
                                  height: 40px;
                                  border-radius: 8px;
                                  display: inline-flex;
                                  align-items: center;
                                  justify-content: center;
                                  margin-right: 12px;">
                        <span style="color: white; font-size: 20px; font-weight: bold;">JH</span>
                      </div>
                      <span style="font-size: 20px; 
                                   font-weight: 600; 
                                   color: #202124;">
                        JobHub
                      </span>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <tr>
            <td style="padding: 40px 40px 30px 40px;">

              <!-- Header -->
              <h1 style="color: #1a73e8; 
                         margin: 0 0 10px 0; 
                         font-size: 24px; 
                         font-weight: 600;
                         line-height: 1.3;">
                New {service_category} job in {postcode}
              </h1>

              <p style="font-size: 16px; 
                        color: #5f6368; 
                        margin: 0 0 30px 0;
                        line-height: 1.5;">
                A homeowner has just posted a new job that matches your trade.
              </p>

              <!-- Job Details Section -->
              <div style="background-color: #f8f9fa; 
                          border-left: 4px solid #1a73e8;
                          padding: 20px;
                          margin: 0 0 30px 0;
                          border-radius: 4px;">
                
                <h2 style="color: #1a73e8; 
                           margin: 0 0 15px 0; 
                           font-size: 18px;
                           font-weight: 600;">
                  Job Details
                </h2>

                <table cellpadding="0" cellspacing="0" border="0" style="width: 100%;">
                  <tr>
                    <td style="padding: 8px 0;">
                      <span style="font-weight: 600; color: #202124;">Job Title:</span>
                      <span style="color: #5f6368; display: block; margin-top: 4px; font-size: 15px;">{job_title}</span>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 8px 0;">
                      <span style="font-weight: 600; color: #202124;">Description:</span>
                      <span style="color: #5f6368; display: block; margin-top: 4px;">{job_description}</span>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 8px 0;">
                      <span style="font-weight: 600; color: #202124;">Budget:</span>
                      <span style="color: #5f6368;">{budget}</span>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding: 8px 0;">
                      <span style="font-weight: 600; color: #202124;">Urgency:</span>
                      <span style="color: #5f6368;">{urgency}</span>
                    </td>
                  </tr>
                </table>
              </div>

              <!-- CTA Button -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" style="padding: 10px 0 30px 0;">
                    <a href="{project_url}"
                       style="background-color: #1a73e8; 
                              color: #ffffff; 
                              padding: 14px 32px; 
                              text-decoration: none; 
                              border-radius: 6px; 
                              font-size: 16px;
                              font-weight: 500;
                              display: inline-block;
                              box-shadow: 0 1px 3px rgba(0,0,0,0.12);">
                      View Job &amp; Respond
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Footer Text -->
              <p style="font-size: 13px; 
                        color: #5f6368; 
                        line-height: 1.6;
                        margin: 0 0 10px 0;">
                You are receiving this notification because your profile matches the homeowner's requested service category.
              </p>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #f8f9fa; 
                       padding: 20px 40px; 
                       border-top: 1px solid #e8eaed;
                       border-radius: 0 0 8px 8px;">
              <p style="font-size: 12px; 
                        color: #5f6368; 
                        margin: 0;
                        text-align: center;">
                © {first_name or "Ivan"} — JobHub Marketplace
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
""".strip()

    return {
        "subject": subject,
        "text_body": text_body,
        "html_body": html_body,
        "context": context,
    }