# orders/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, retry_kwargs={'max_retries': 3, 'countdown': 60})
def send_order_completion_email(self, order_id, customer_email, customer_name, client_id):
    """
    Send order completion notification email to customer
    """
    try:
        subject = f'🎉 Your Order {order_id} is Ready!'
        
        # Create email content
        message = f"""
Dear {customer_name},

Great news! Your jewelry order has been completed and is ready for pickup/delivery.

Order Details:
📋 Order ID: {order_id}
👤 Client ID: {client_id}
📧 Email: {customer_email}

Please visit our store with your order ID to collect your beautiful jewelry piece.

If you have any questions, please don't hesitate to contact us.

Thank you for choosing Royal Craft Jewelers!

Best regards,
Royal Craft Jewelers Team
        """
        
        # Send email
        result = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer_email],
            fail_silently=False,
        )
        
        logger.info(f"Order completion email sent successfully for order {order_id}")
        return f"Email sent successfully to {customer_email}"
        
    except Exception as exc:
        logger.error(f"Failed to send email for order {order_id}: {str(exc)}")
        # Retry the task
        raise self.retry(exc=exc)

@shared_task
def send_order_status_update_email(order_id, customer_email, customer_name, old_status, new_status):
    """
    Send order status update notification
    """
    try:
        subject = f'Order Update: {order_id} - Status Changed'
        
        message = f"""
Dear {customer_name},

Your order status has been updated:

📋 Order ID: {order_id}
📊 Previous Status: {old_status.replace('_', ' ').title()}
📊 Current Status: {new_status.replace('_', ' ').title()}

You can track your order status anytime using your Order ID and Client ID.

Thank you for your patience!

Best regards,
Royal Craft Jewelers Team
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer_email],
            fail_silently=False,
        )
        
        logger.info(f"Status update email sent for order {order_id}")
        return f"Status update email sent to {customer_email}"
        
    except Exception as exc:
        logger.error(f"Failed to send status update email for order {order_id}: {str(exc)}")
        raise exc
