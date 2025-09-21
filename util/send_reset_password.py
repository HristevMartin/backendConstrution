from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from config import Config

APP_NAME = Config.COMPANY_NAME or "JobHub"
FROM_EMAIL = Config.SENDGRID_FROM_EMAIL
API_KEY = Config.SENDGRID_API_KEY

def _send_reset_email(to_email: str, reset_link: str) -> None:
    if not API_KEY or not FROM_EMAIL:
        print(f"[DEV] Password reset link for {to_email}: {reset_link}")
        return

    subject = f"Reset your {APP_NAME} password"
    html = (
        f"<p>We received a request to reset your password.</p>"
        f"<p><a href=\"{reset_link}\">Reset Password</a></p>"
        f"<p>This link expires soon. If you didn’t request this, you can ignore the email.</p>"
    )

    msg = Mail(
        from_email=(FROM_EMAIL, APP_NAME),
        to_emails=to_email,
        subject=subject,
        html_content=html,
        plain_text_content=f"Reset your password: {reset_link}",
    )

    try:
        SendGridAPIClient(API_KEY).send(msg)
    except Exception as e:
        print(f"[Email] SendGrid error sending to {to_email}: {e}")
