# orders/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from .models import Order
from .tasks import send_order_completion_email, send_order_status_update_email
import logging
from django.conf import settings

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

@receiver(post_save, sender=Order)
def send_order_notification_email(sender, instance, created, **kwargs):
    """
    Send email notifications when order status changes
    """
    if not settings.ENABLE_BACKGROUND_TASKS:
        return
    if created:
        # Don't send email when order is first created
        return
    
    old_status = getattr(instance, '_old_status', None)
    new_status = instance.order_status
    
    # Only send email if status actually changed
    if old_status and old_status != new_status:
        # Schedule email task to run after transaction commits
        transaction.on_commit(lambda: handle_status_change_email(instance, old_status, new_status))

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
