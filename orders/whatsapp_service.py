# orders/whatsapp_service.py
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def send_whatsapp_message(phone_number, message):
    """
    Send WhatsApp message via Evolution API
    """
    base_url = getattr(settings, 'WHATSAPP_API_BASE_URL', 'http://localhost:8080')
    api_key = getattr(settings, 'WHATSAPP_API_KEY', 'C74709FD0F08-43B5-BA0C-D76E962F33EC')
    instance_name = getattr(settings, 'WHATSAPP_INSTANCE_NAME', 'test')
    
    url = f"{base_url}/message/sendText/{instance_name}"
    
    headers = {
        "Content-Type": "application/json",
        "apikey": api_key
    }
    
    payload = {
        "number": phone_number,
        "text": message,
        "delay": 500,
        "linkPreview": False
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"WhatsApp message sent to {phone_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to send WhatsApp to {phone_number}: {str(e)}")
        return False

