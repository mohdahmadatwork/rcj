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

# @receiver(post_save, sender=Order)
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
            transaction.on_commit(lambda: handle_order_status_change_whatsapp(instance))
        
        # Schedule email task to run after transaction commits
        if settings.ENABLE_BACKGROUND_TASKS:
            transaction.on_commit(lambda: handle_status_change_email(instance, old_status, new_status))

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction

# Step 1: Capture old status BEFORE save
@receiver(pre_save, sender=Order)
def capture_old_status(sender, instance, **kwargs):
    """Store old status before it gets updated"""
    if instance.pk:  # Only if it's an existing order (not new)
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            instance._old_status = old_instance.order_status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


# Step 2: Send notifications AFTER save
@receiver(post_save, sender=Order)
def send_order_notifications(sender, instance, created, **kwargs):
    """Send notifications when order is created or status changes"""
    
    if created:
        # New order created
        if settings.ENABLE_WHATSAPP_TASKS:
            transaction.on_commit(lambda: handle_new_order_whatsapp(instance))
        return
    
    # Check if status changed
    old_status = getattr(instance, '_old_status', None)
    new_status = instance.order_status
    
    if old_status and old_status != new_status:
        # Status changed - send notifications
        if settings.ENABLE_WHATSAPP_TASKS:
            transaction.on_commit(lambda: handle_order_status_change_whatsapp(instance))
        
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

def handle_order_status_change_whatsapp(instance):
    """Send WhatsApp notification for order status change"""
    
    if not instance.contact_number:
        logger.warning(f"No contact number for order {instance.order_id}")
        return
    
    phone_number = format_phone_number(instance.contact_number)
    if not phone_number:
        logger.warning(f"Invalid phone number for order {instance.order_id}")
        return
    
    # Hardcoded messages for each status
    messages = {
        'new': f"Hi {instance.full_name}! We received your order {instance.order_id}. Thank you!",
        'confirmed': f"Your order {instance.order_id} is confirmed. Design work starting now.",
        'cad_done': f"CAD design for order {instance.order_id} is complete!",
        'user_confirmed': f"Great! You approved the design for order {instance.order_id}. Moving to manufacturing.",
        'rpt_done': f"Your order {instance.order_id} passed quality review.",
        'casting': f"Your order {instance.order_id} is in casting phase.",
        'ready': f"Your order {instance.order_id} is ready for delivery!",
        'delivered': f"Your order {instance.order_id} has been delivered. Thank you!",
        'declined': f"Your order {instance.order_id} could not be processed. Contact support.",
    }
    
    message = messages.get(instance.status)
    if not message:
        logger.warning(f"No message for status {instance.status}")
        return
    
    try:
        send_whatsapp_message(phone_number, message)
        logger.info(f"WhatsApp sent for order {instance.order_id} - Status: {instance.status}")
    except Exception as e:
        logger.error(f"Error sending WhatsApp for order {instance.order_id}: {str(e)}")
        
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
