#!/usr/bin/env python3
"""
Quick SendGrid API key test script
"""
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

# Replace with your new API key
API_KEY = os.getenv('SENDGRID_API_KEY', 'YOUR_NEW_API_KEY_HERE')
FROM_EMAIL = 'info@find-tradespeople.com'
TO_EMAIL = 'hristevmartin96@gmail.com'  # Your test email

def test_sendgrid():
    """Test if SendGrid API key is valid"""
    print(f"🔑 Testing API Key: {API_KEY[:15]}...")
    print(f"📧 From: {FROM_EMAIL}")
    print(f"📧 To: {TO_EMAIL}")
    
    try:
        # Create SendGrid client
        sg = SendGridAPIClient(api_key=API_KEY)
        
        # Test 1: Check API key validity
        print("\n✅ Test 1: Checking API key validity...")
        response = sg.client.api_keys.get()
        print(f"   Status: {response.status_code} - API key is valid!")
        
        # Test 2: Send a test email
        print("\n✅ Test 2: Sending test email...")
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=TO_EMAIL,
            subject='SendGrid Test Email',
            html_content='<p>This is a test email from your Flask app.</p>'
        )
        
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            print(f"   ✅ Email sent successfully! Status: {response.status_code}")
            print(f"   Check {TO_EMAIL} for the test email.")
            return True
        else:
            print(f"   ❌ Failed to send email. Status: {response.status_code}")
            print(f"   Response: {response.body}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nPossible issues:")
        print("1. Invalid API key - create a new one in SendGrid")
        print("2. Sender email not verified - verify in SendGrid")
        print("3. API key missing 'Mail Send' permission")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🧪 SendGrid API Key Test")
    print("=" * 50)
    
    if API_KEY == 'YOUR_NEW_API_KEY_HERE':
        print("\n⚠️  Please set SENDGRID_API_KEY environment variable or edit this file")
        print("   export SENDGRID_API_KEY='SG.your_key_here'  # Linux/Mac")
        print("   $env:SENDGRID_API_KEY='SG.your_key_here'   # Windows PowerShell")
    else:
        test_sendgrid()
    
    print("\n" + "=" * 50)

