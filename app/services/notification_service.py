import os
from datetime import datetime
from app.models.reminder import Channel
import pytz

IST = pytz.timezone("Asia/Kolkata")

# ── Message Templates ──────────────────────────────────────
# WHY templates per language: Patient receives message in their
# own language = higher chance they read it and return.

TEMPLATES = {
    "followup_3d": {
        "en": "Dear {name}, Dr. {doctor} from {clinic} is following up on your recent visit. How are you feeling? Please visit us if needed. Call: {phone}",
        "hi": "प्रिय {name}, {clinic} से Dr. {doctor} आपकी देखभाल के लिए संपर्क कर रहे हैं। आप कैसा महसूस कर रहे हैं? जरूरत हो तो आएं। Call: {phone}",
        "mr": "प्रिय {name}, {clinic} मधून Dr. {doctor} तुमची काळजी घेत आहेत। तुम्ही कसे आहात? गरज असल्यास भेट द्या। Call: {phone}",
    },
    "followup_7d": {
        "en": "Dear {name}, it's been a week since your visit at {clinic}. Dr. {doctor} recommends a follow-up. Book your appointment: {phone}",
        "hi": "प्रिय {name}, {clinic} में आपकी visit को एक सप्ताह हो गया है। Dr. {doctor} follow-up की सलाह देते हैं। संपर्क करें: {phone}",
        "mr": "प्रिय {name}, {clinic} ला भेट देऊन एक आठवडा झाला. Dr. {doctor} follow-up सुचवतात. संपर्क: {phone}",
    },
    "followup_15d": {
        "en": "Dear {name}, Dr. {doctor} from {clinic} would like to check on your progress. Please schedule your follow-up visit. Call: {phone}",
        "hi": "प्रिय {name}, Dr. {doctor} आपकी प्रगति जानना चाहते हैं। कृपया follow-up के लिए आएं। Call: {phone}",
        "mr": "प्रिय {name}, Dr. {doctor} तुमची प्रगती जाणून घेऊ इच्छितात. Follow-up साठी या. Call: {phone}",
    },
    "followup_monthly": {
        "en": "Dear {name}, your monthly check-up is due at {clinic}. Dr. {doctor} is expecting you. Call: {phone}",
        "hi": "प्रिय {name}, {clinic} में आपका monthly check-up बाकी है। Dr. {doctor} आपका इंतज़ार कर रहे हैं। Call: {phone}",
        "mr": "प्रिय {name}, {clinic} मध्ये तुमची monthly तपासणी बाकी आहे. Dr. {doctor} वाट पाहत आहेत. Call: {phone}",
    },
    "thankyou": {
        "en": "Dear {name}, thank you for visiting {clinic}. Dr. {doctor} wishes you a speedy recovery. For queries call: {phone}",
        "hi": "प्रिय {name}, {clinic} में आने के लिए धन्यवाद। Dr. {doctor} आपके शीघ्र स्वास्थ्य की कामना करते हैं। Call: {phone}",
        "mr": "प्रिय {name}, {clinic} ला भेट दिल्याबद्दल धन्यवाद. Dr. {doctor} तुमच्या लवकर बरे होण्याची इच्छा करतात. Call: {phone}",
    },
    "birthday": {
        "en": "Dear {name}, wishing you a very Happy Birthday! From Dr. {doctor} and the team at {clinic}. Stay healthy! 🎂",
        "hi": "प्रिय {name}, आपको जन्मदिन की हार्दिक शुभकामनाएं! Dr. {doctor} और {clinic} की पूरी टीम की ओर से। स्वस्थ रहें! 🎂",
        "mr": "प्रिय {name}, तुम्हाला वाढदिवसाच्या हार्दिक शुभेच्छा! Dr. {doctor} आणि {clinic} टीमकडून. निरोगी राहा! 🎂",
    }
}

def get_template(template_key: str, language: str) -> str:
    """Get message template for given key and language"""
    templates = TEMPLATES.get(template_key, TEMPLATES["followup_7d"])
    # Fall back to English if language not found
    return templates.get(language, templates["en"])

def fill_template(template: str, patient_name: str,
                  doctor_name: str, clinic_name: str,
                  clinic_phone: str) -> str:
    """Fill template variables with real data"""
    return template.format(
        name    = patient_name,
        doctor  = doctor_name,
        clinic  = clinic_name,
        phone   = clinic_phone
    )

# ── Sending Functions ──────────────────────────────────────

def send_whatsapp(phone: str, message: str) -> dict:
    """
    Send WhatsApp message via Twilio.
    Currently MOCKED — logs message instead of sending.
    To activate: add TWILIO credentials to .env
    WHY mock first: Build and test entire flow without paying Twilio.
    Switch to real sending by changing 3 lines only.
    """
    twilio_sid   = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_from  = os.getenv("TWILIO_WHATSAPP_FROM", "")

    # If Twilio credentials exist — send real message
    if twilio_sid and twilio_token and twilio_from:
        try:
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_token)
            msg = client.messages.create(
                from_ = f"whatsapp:{twilio_from}",
                to    = f"whatsapp:+91{phone}",
                body  = message
            )
            return {
                "status":  "sent",
                "channel": "whatsapp",
                "sid":     msg.sid,
                "phone":   phone
            }
        except Exception as e:
            return {
                "status":  "failed",
                "channel": "whatsapp",
                "error":   str(e),
                "phone":   phone
            }

    # MOCK — just log it
    print(f"\n📱 WHATSAPP MOCK")
    print(f"   To:      +91{phone}")
    print(f"   Message: {message}")
    print(f"   Time:    {datetime.now(IST).strftime('%d-%m-%Y %H:%M')}\n")

    return {
        "status":  "mocked",
        "channel": "whatsapp",
        "phone":   phone,
        "message": message,
        "note":    "Add Twilio credentials to .env to send real messages"
    }

def send_sms(phone: str, message: str) -> dict:
    """
    Send SMS via Twilio.
    Used as fallback if WhatsApp fails.
    """
    twilio_sid   = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")

    if twilio_sid and twilio_token:
        try:
            from twilio.rest import Client
            client  = Client(twilio_sid, twilio_token)
            msg = client.messages.create(
                from_ = os.getenv("TWILIO_SMS_FROM", ""),
                to    = f"+91{phone}",
                body  = message
            )
            return {"status": "sent", "channel": "sms", "sid": msg.sid}
        except Exception as e:
            return {"status": "failed", "channel": "sms", "error": str(e)}

    # MOCK
    print(f"\n📨 SMS MOCK")
    print(f"   To:      +91{phone}")
    print(f"   Message: {message}\n")

    return {
        "status":  "mocked",
        "channel": "sms",
        "phone":   phone,
        "message": message
    }

def send_notification(channel: str, phone: str,
                      message: str) -> dict:
    """
    Route to correct channel.
    WHY single entry point: Caller doesn't need to know
    which channel — just calls send_notification().
    """
    if channel == "WHATSAPP":
        return send_whatsapp(phone, message)
    elif channel == "SMS":
        return send_sms(phone, message)
    else:
        return send_whatsapp(phone, message)  # default to WhatsApp