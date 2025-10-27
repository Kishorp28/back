import os
from dotenv import load_dotenv
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "Recruiter AI")

# Configure API client
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = BREVO_API_KEY
api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

def send_email(name, recipient_email, job_title):
    subject = f"Interview Shortlist Notification for {job_title}"
    html_content = f"""
    <p>Dear {name},</p>
    <p>Congratulations! You have been shortlisted for the <b>{job_title}</b> position.</p>
    <p>Best regards,<br>Recruiter AI Team</p>
    """
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": recipient_email, "name": name}],
        sender={"email": BREVO_SENDER_EMAIL, "name": BREVO_SENDER_NAME},
        subject=subject,
        html_content=html_content
    )

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        print(f"✅ Email sent to {recipient_email}")
        return "Email sent successfully"
    except ApiException as e:
        print(f"❌ Exception while sending to {recipient_email}: {e.body}")
        return e.body
