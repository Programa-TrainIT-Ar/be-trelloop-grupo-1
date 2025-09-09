import os
import requests

RESEND_API = "https://api.resend.com/emails"

def send_email(to: str, subject: str, html: str) -> bool:
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("RESEND_FROM")
    if not api_key or not sender:
        # Si no está configurado, no falles toda la request
        return False

    resp = requests.post(
        RESEND_API,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "from": sender,
            "to": [to],
            "subject": subject,
            "html": html,
        },
        timeout=10,
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
    return resp.status_code in (200, 202)