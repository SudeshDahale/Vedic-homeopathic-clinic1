import httpx
import os
from datetime import datetime
from sqlalchemy.orm import Session
import pytz

IST = pytz.timezone("Asia/Kolkata")

def get_headers() -> dict:
    token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json"
    }

def get_api_url() -> str:
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    base_url        = os.getenv("WHATSAPP_API_URL",
                                "https://graph.facebook.com/v19.0")
    return f"{base_url}/{phone_number_id}/messages"

async def send_text_message(phone: str, message: str) -> dict:
    """
    Send plain text WhatsApp message.
    WHY async: WhatsApp API call should not block main server.
    Patient gets message while doctor continues working.
    """
    # Check credentials exist
    if not os.getenv("WHATSAPP_ACCESS_TOKEN"):
        # Fall back to mock
        print(f"\n📱 WHATSAPP MOCK (no credentials)")
        print(f"   To:      +91{phone}")
        print(f"   Message: {message}\n")
        return {
            "status":  "mocked",
            "phone":   phone,
            "message": message
        }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                f"91{phone}",
        "type":              "text",
        "text":              {"body": message}
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                get_api_url(),
                headers = get_headers(),
                json    = payload,
                timeout = 10.0
            )
            data = response.json()

            if response.status_code == 200:
                message_id = data.get("messages", [{}])[0].get("id", "")
                return {
                    "status":     "sent",
                    "message_id": message_id,
                    "phone":      phone
                }
            else:
                return {
                    "status": "failed",
                    "error":  data.get("error", {}).get("message", "Unknown error"),
                    "phone":  phone
                }
        except Exception as e:
            return {
                "status": "failed",
                "error":  str(e),
                "phone":  phone
            }

async def send_template_message(phone: str, template_name: str,
                                language: str, components: list) -> dict:
    """
    Send approved WhatsApp template message.
    WHY templates: Meta requires pre-approved templates
    for business-initiated conversations.
    After approval — higher delivery rate, no spam filtering.
    """
    if not os.getenv("WHATSAPP_ACCESS_TOKEN"):
        print(f"\n📱 TEMPLATE MOCK: {template_name} → +91{phone}\n")
        return {"status": "mocked", "template": template_name}

    payload = {
        "messaging_product": "whatsapp",
        "to":                f"91{phone}",
        "type":              "template",
        "template": {
            "name":       template_name,
            "language":   {"code": language},
            "components": components
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                get_api_url(),
                headers = get_headers(),
                json    = payload,
                timeout = 10.0
            )
            data = response.json()

            if response.status_code == 200:
                return {
                    "status":     "sent",
                    "message_id": data.get("messages", [{}])[0].get("id", ""),
                    "template":   template_name
                }
            else:
                return {
                    "status": "failed",
                    "error":  data.get("error", {}).get("message", "Unknown"),
                    "phone":  phone
                }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

async def send_followup_reminder(phone: str, patient_name: str,
                                 doctor_name: str, clinic_name: str,
                                 clinic_phone: str, language: str = "en",
                                 followup_type: str = "followup_7d") -> dict:
    """
    Send follow-up reminder message.
    WHY: This is the core revenue driver.
    Patient gets reminded → comes back → doctor earns.
    """
    from app.services.notification_service import get_template, fill_template

    template = get_template(followup_type, language)
    message  = fill_template(
        template     = template,
        patient_name = patient_name,
        doctor_name  = doctor_name,
        clinic_name  = clinic_name,
        clinic_phone = clinic_phone
    )

    return await send_text_message(phone, message)

async def send_thankyou_message(phone: str, patient_name: str,
                                doctor_name: str, clinic_name: str,
                                clinic_phone: str,
                                language: str = "en") -> dict:
    """
    Send thank-you after visit closes.
    WHY: Patient feels valued → more likely to return + refer.
    Sent automatically — doctor does nothing.
    """
    from app.services.notification_service import get_template, fill_template

    template = get_template("thankyou", language)
    message  = fill_template(
        template     = template,
        patient_name = patient_name,
        doctor_name  = doctor_name,
        clinic_name  = clinic_name,
        clinic_phone = clinic_phone
    )

    return await send_text_message(phone, message)

async def send_birthday_message(phone: str, patient_name: str,
                                doctor_name: str, clinic_name: str,
                                language: str = "en") -> dict:
    """
    Birthday greeting — builds emotional connection.
    WHY: Patient remembers clinic on their birthday.
    Most clinics never do this — massive differentiation.
    """
    from app.services.notification_service import get_template, fill_template

    template = get_template("birthday", language)
    message  = fill_template(
        template     = template,
        patient_name = patient_name,
        doctor_name  = doctor_name,
        clinic_name  = clinic_name,
        clinic_phone = ""
    )

    return await send_text_message(phone, message)