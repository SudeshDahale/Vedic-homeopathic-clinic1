import httpx
import os

from datetime import datetime

from sqlalchemy.orm import Session

import pytz


# =====================================================
# TIMEZONE
# =====================================================

IST = pytz.timezone("Asia/Kolkata")


# =====================================================
# PHONE NORMALIZATION
# =====================================================

def normalize_phone(phone: str) -> str:
    """
    Normalize Indian phone numbers safely.

    Examples:
    9876543210      -> 919876543210
    +919876543210   -> 919876543210
    91 9876543210   -> 919876543210
    """

    if not phone:
        return ""

    phone = (
        phone.strip()
        .replace(" ", "")
        .replace("-", "")
    )

    # Remove +
    if phone.startswith("+"):
        phone = phone[1:]

    # Add India country code if missing
    if not phone.startswith("91"):
        phone = f"91{phone}"

    return phone


# =====================================================
# HEADERS
# =====================================================

def get_headers() -> dict:

    token = os.getenv(
        "WHATSAPP_ACCESS_TOKEN",
        ""
    )

    return {

        "Authorization":
            f"Bearer {token}",

        "Content-Type":
            "application/json"
    }


# =====================================================
# API URL
# =====================================================

def get_api_url() -> str:

    phone_number_id = os.getenv(
        "WHATSAPP_PHONE_NUMBER_ID",
        ""
    )

    base_url = os.getenv(
        "WHATSAPP_API_URL",
        "https://graph.facebook.com/v19.0"
    )

    return f"{base_url}/{phone_number_id}/messages"


# =====================================================
# SEND TEXT MESSAGE
# =====================================================

async def send_text_message(
    phone: str,
    message: str
) -> dict:
    """
    Send plain text WhatsApp message.
    """

    normalized_phone = normalize_phone(phone)

    # -------------------------------------------------
    # MOCK MODE
    # -------------------------------------------------

    if not os.getenv("WHATSAPP_ACCESS_TOKEN"):

        print(f"\n📱 WHATSAPP MOCK")
        print(f"   To:      +{normalized_phone}")
        print(f"   Message: {message}\n")

        return {

            "status":
                "mocked",

            "phone":
                normalized_phone,

            "message":
                message
        }

    # -------------------------------------------------
    # PAYLOAD
    # -------------------------------------------------

    payload = {

        "messaging_product":
            "whatsapp",

        "recipient_type":
            "individual",

        "to":
            normalized_phone,

        "type":
            "text",

        "text": {
            "body": message
        }
    }

    # -------------------------------------------------
    # API CALL
    # -------------------------------------------------

    async with httpx.AsyncClient() as client:

        try:

            response = await client.post(

                get_api_url(),

                headers=get_headers(),

                json=payload,

                timeout=10.0
            )

            data = response.json()

            if response.status_code == 200:

                message_id = data.get(
                    "messages",
                    [{}]
                )[0].get(
                    "id",
                    ""
                )

                return {

                    "status":
                        "sent",

                    "message_id":
                        message_id,

                    "phone":
                        normalized_phone
                }

            else:

                return {

                    "status":
                        "failed",

                    "error":
                        data.get(
                            "error",
                            {}
                        ).get(
                            "message",
                            "Unknown error"
                        ),

                    "phone":
                        normalized_phone
                }

        except Exception as e:

            return {

                "status":
                    "failed",

                "error":
                    str(e),

                "phone":
                    normalized_phone
            }


# =====================================================
# SEND TEMPLATE MESSAGE
# =====================================================

async def send_template_message(
    phone: str,
    template_name: str,
    language: str,
    components: list
) -> dict:
    """
    Send approved WhatsApp template message.
    """

    normalized_phone = normalize_phone(phone)

    # -------------------------------------------------
    # MOCK MODE
    # -------------------------------------------------

    if not os.getenv("WHATSAPP_ACCESS_TOKEN"):

        print(
            f"\n📱 TEMPLATE MOCK: "
            f"{template_name} → +{normalized_phone}\n"
        )

        return {

            "status":
                "mocked",

            "template":
                template_name
        }

    # -------------------------------------------------
    # PAYLOAD
    # -------------------------------------------------

    payload = {

        "messaging_product":
            "whatsapp",

        "to":
            normalized_phone,

        "type":
            "template",

        "template": {

            "name":
                template_name,

            "language": {
                "code": language
            },

            "components":
                components
        }
    }

    # -------------------------------------------------
    # API CALL
    # -------------------------------------------------

    async with httpx.AsyncClient() as client:

        try:

            response = await client.post(

                get_api_url(),

                headers=get_headers(),

                json=payload,

                timeout=10.0
            )

            data = response.json()

            if response.status_code == 200:

                return {

                    "status":
                        "sent",

                    "message_id":
                        data.get(
                            "messages",
                            [{}]
                        )[0].get(
                            "id",
                            ""
                        ),

                    "template":
                        template_name
                }

            else:

                return {

                    "status":
                        "failed",

                    "error":
                        data.get(
                            "error",
                            {}
                        ).get(
                            "message",
                            "Unknown"
                        ),

                    "phone":
                        normalized_phone
                }

        except Exception as e:

            return {

                "status":
                    "failed",

                "error":
                    str(e)
            }


# =====================================================
# FOLLOWUP REMINDER
# =====================================================

async def send_followup_reminder(

    phone: str,

    patient_name: str,

    doctor_name: str,

    clinic_name: str,

    clinic_phone: str,

    language: str = "en",

    followup_type: str = "followup_7d"
) -> dict:
    """
    Send follow-up reminder.
    """

    from app.services.notification_service import (
        get_template,
        fill_template
    )

    template = get_template(
        followup_type,
        language
    )

    message = fill_template(

        template=template,

        patient_name=patient_name,

        doctor_name=doctor_name,

        clinic_name=clinic_name,

        clinic_phone=clinic_phone
    )

    return await send_text_message(
        phone,
        message
    )


# =====================================================
# THANK YOU MESSAGE
# =====================================================

async def send_thankyou_message(

    phone: str,

    patient_name: str,

    doctor_name: str,

    clinic_name: str,

    clinic_phone: str,

    language: str = "en"
) -> dict:
    """
    Send thank-you message.
    """

    from app.services.notification_service import (
        get_template,
        fill_template
    )

    template = get_template(
        "thankyou",
        language
    )

    message = fill_template(

        template=template,

        patient_name=patient_name,

        doctor_name=doctor_name,

        clinic_name=clinic_name,

        clinic_phone=clinic_phone
    )

    return await send_text_message(
        phone,
        message
    )


# =====================================================
# BIRTHDAY MESSAGE
# =====================================================

async def send_birthday_message(

    phone: str,

    patient_name: str,

    doctor_name: str,

    clinic_name: str,

    language: str = "en"
) -> dict:
    """
    Send birthday greeting.
    """

    from app.services.notification_service import (
        get_template,
        fill_template
    )

    template = get_template(
        "birthday",
        language
    )

    message = fill_template(

        template=template,

        patient_name=patient_name,

        doctor_name=doctor_name,

        clinic_name=clinic_name,

        clinic_phone=""
    )

    return await send_text_message(
        phone,
        message
    )