# orders/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from .models import Order
from .tasks import send_order_completion_email, send_order_status_update_email
from .whatsapp_service import send_whatsapp_message
import logging
from django.conf import settings
import re

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Order)
def capture_old_status(sender, instance, **kwargs):
    """Capture the old status before saving"""
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            instance._old_status = old_instance.order_status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

def format_phone_number(phone_number):
    """
    Format phone number for WhatsApp API (remove spaces, dashes, and ensure country code format)
    Expected format: country code + number (e.g., 919650436187)
    """
    if not phone_number:
        return None
    
    # Remove all non-digit characters
    cleaned = re.sub(r'\D', '', phone_number)
    
    # If number doesn't start with country code, assume it's Indian (+91)
    if len(cleaned) == 10:
        cleaned = '91' + cleaned
    
    return cleaned

@receiver(post_save, sender=Order)
def send_order_notification_email(sender, instance, created, **kwargs):
    """
    Send email and WhatsApp notifications when order is created or status changes
    """
    if created:
        # Send WhatsApp notification for new order
        transaction.on_commit(lambda: handle_new_order_whatsapp(instance))
        # Don't send email when order is first created
        return
    
    old_status = getattr(instance, '_old_status', None)
    new_status = instance.order_status
    
    # Only send notifications if status actually changed
    if old_status and old_status != new_status:
        # Send WhatsApp notification when order is ready for delivery
        if new_status == 'ready':
            transaction.on_commit(lambda: handle_ready_order_whatsapp(instance))
        
        # Schedule email task to run after transaction commits
        if settings.ENABLE_BACKGROUND_TASKS:
            transaction.on_commit(lambda: handle_status_change_email(instance, old_status, new_status))

def handle_new_order_whatsapp(instance):
    """Send WhatsApp notification when a new order is created"""
    if not instance.contact_number:
        logger.warning(f"No contact number for order {instance.order_id}, skipping WhatsApp notification")
        return
    
    phone_number = format_phone_number(instance.contact_number)
    if not phone_number:
        logger.warning(f"Invalid phone number format for order {instance.order_id}, skipping WhatsApp notification")
        return
    
    message = f"Hello {instance.full_name}! Your order {instance.order_id} has been successfully placed. We will keep you updated on the progress. Thank you for choosing us!"
    
    try:
        success = send_whatsapp_message(phone_number, message)
        if success:
            logger.info(f"WhatsApp notification sent for new order {instance.order_id} to {phone_number}")
        else:
            logger.error(f"Failed to send WhatsApp notification for new order {instance.order_id}")
    except Exception as e:
        logger.error(f"Error sending WhatsApp notification for new order {instance.order_id}: {str(e)}")

def handle_ready_order_whatsapp(instance):
    """Send WhatsApp notification when order is ready for delivery"""
    if not instance.contact_number:
        logger.warning(f"No contact number for order {instance.order_id}, skipping WhatsApp notification")
        return
    
    phone_number = format_phone_number(instance.contact_number)
    if not phone_number:
        logger.warning(f"Invalid phone number format for order {instance.order_id}, skipping WhatsApp notification")
        return
    
    message = f"Hello {instance.full_name}! Great news! Your order {instance.order_id} is ready for delivery. We will contact you soon to arrange the delivery. Thank you!"
    
    try:
        success = send_whatsapp_message(phone_number, message)
        if success:
            logger.info(f"WhatsApp notification sent for ready order {instance.order_id} to {phone_number}")
        else:
            logger.error(f"Failed to send WhatsApp notification for ready order {instance.order_id}")
    except Exception as e:
        logger.error(f"Error sending WhatsApp notification for ready order {instance.order_id}: {str(e)}")

def handle_status_change_email(instance, old_status, new_status):
    """Handle email sending based on status change"""
    if not settings.ENABLE_BACKGROUND_TASKS:
        return
    # Send completion email when order is ready or delivered
    if new_status in ['ready', 'delivered']:
        send_order_completion_email.delay(
            order_id=instance.order_id,
            customer_email=instance.email,
            customer_name=instance.full_name,
            client_id=instance.client_id
        )
        logger.info(f"Queued completion email for order {instance.order_id}")
    
    # Send status update email for other status changes
    elif new_status not in ['new', 'declined']:
        send_order_status_update_email.delay(
            order_id=instance.order_id,
            customer_email=instance.email,
            customer_name=instance.full_name,
            old_status=old_status,
            new_status=new_status
        )
        logger.info(f"Queued status update email for order {instance.order_id}")
