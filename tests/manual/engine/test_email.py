"""
Test script to send a sample alert email
Usage: python tests/manual/engine/test_email.py
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).resolve().parents[3] / 'engine' / '.env'
load_dotenv(env_path)

def send_test_email():
    """Send a test alert email"""

    # Get email configuration from environment
    email_host = os.getenv('EMAIL_HOST', 'smtp.mailgun.org')
    email_port = int(os.getenv('EMAIL_PORT', 587))
    email_use_tls = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
    email_host_user = os.getenv('EMAIL_HOST_USER', '')
    email_host_password = os.getenv('EMAIL_HOST_PASSWORD', '')
    default_from_email = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@example.com')
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8080')

    print("="*60)
    print("Email Configuration:")
    print(f"  Host: {email_host}")
    print(f"  Port: {email_port}")
    print(f"  TLS: {email_use_tls}")
    print(f"  From: {default_from_email}")
    print(f"  User: {email_host_user}")
    print("="*60)

    if not email_host_user or not email_host_password:
        print("ERROR: Email credentials not configured in .env file")
        return False

    # Test recipient
    recipient = "sarvanan@appkodes.com"

    # Prepare test email content
    subject = "[TEST] LLM Monitor Alert System - Email Verification"
    body = f"""
Hello,

This is a test email to verify the LLM Monitor alert notification system.

Test Alert Details:
------------------
Title: Email System Verification Test
Message: This is a sample alert to verify that the email notification system is working correctly.
Severity: MEDIUM
Domain: test-domain.com
Metric: -15.5%
Status: Active

Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

If you receive this email, it means the alert email system is configured correctly and working as expected.

View in dashboard: {frontend_url}/alerts

---
LLM Monitor Alert System
Powered by Mailgun SMTP
"""

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = default_from_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        print(f"\nSending test email to: {recipient}")
        print(f"Subject: {subject}")
        print("\nConnecting to SMTP server...")

        # Connect to SMTP server and send
        with smtplib.SMTP(email_host, email_port, timeout=10) as server:
            print(f"Connected to {email_host}:{email_port}")

            if email_use_tls:
                print("Starting TLS...")
                server.starttls()

            print("Logging in...")
            server.login(email_host_user, email_host_password)

            print("Sending email...")
            server.send_message(msg)

        print("\n" + "="*60)
        print("✓ SUCCESS: Test email sent successfully!")
        print(f"✓ Check inbox at: {recipient}")
        print("="*60)
        return True

    except smtplib.SMTPAuthenticationError as e:
        print("\n" + "="*60)
        print("✗ ERROR: SMTP Authentication Failed")
        print(f"  {str(e)}")
        print("  Check your EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env")
        print("="*60)
        return False

    except smtplib.SMTPException as e:
        print("\n" + "="*60)
        print("✗ ERROR: SMTP Error")
        print(f"  {str(e)}")
        print("="*60)
        return False

    except Exception as e:
        print("\n" + "="*60)
        print("✗ ERROR: Failed to send email")
        print(f"  {str(e)}")
        print("="*60)
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("LLM Monitor - Email System Test")
    print("="*60)
    send_test_email()
