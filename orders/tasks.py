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



# orders/tasks.py (ADD THESE NEW TASKS)

from celery import shared_task
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.core.management import call_command
from datetime import date, datetime
import logging
import os

logger = logging.getLogger(__name__)

# ... your existing tasks ...

@shared_task(bind=True, retry_kwargs={'max_retries': 2, 'countdown': 300})
def create_daily_backup_and_email(self):
    """
    Creates daily backup (Excel) and emails it to admin
    Runs automatically at 12:00 AM daily
    """
    try:
        from io import StringIO
        
        logger.info("Starting daily backup task...")
        
        # Get yesterday's date (since this runs at midnight)
        backup_date = date.today()
        
        # Capture command output
        output = StringIO()
        call_command('backup_daily_data', stdout=output)
        output_text = output.getvalue()
        
        # Extract file path from output
        backup_file_path = None
        if 'File saved:' in output_text:
            backup_file_path = output_text.split('File saved:')[-1].strip()
        
        if not backup_file_path or not os.path.exists(backup_file_path):
            raise Exception("Backup file not found after creation")
        
        # Get file size
        file_size_mb = os.path.getsize(backup_file_path) / (1024 * 1024)
        
        # Count records from output
        total_records = 0
        for line in output_text.split('\n'):
            if 'Total records:' in line:
                try:
                    total_records = int(line.split(':')[1].strip())
                except:
                    pass
        
        # Prepare email
        subject = f'📊 Daily Backup Report - {backup_date.strftime("%B %d, %Y")}'
        
        message = f"""
Daily Database Backup Completed Successfully!

Backup Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 Date: {backup_date.strftime("%B %d, %Y")}
⏰ Time: {datetime.now().strftime("%I:%M %p")}
📊 Total Records: {total_records}
📦 File Size: {file_size_mb:.2f} MB
📁 File Name: {os.path.basename(backup_file_path)}

Backup includes data from all models:
✓ Users
✓ Orders
✓ Order Files
✓ Order Logs
✓ Messages
✓ Contacts
✓ Work Samples
✓ Categories
✓ News Items
✓ News Read Tracker
✓ News Images

The Excel backup file is attached to this email.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Automated Backup System
Royal Craft Jewelers
        """
        
        # Create email with attachment
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.ADMIN_EMAIL],  # Make sure this is set in settings.py
        )
        
        # Attach backup file
        with open(backup_file_path, 'rb') as f:
            email.attach(
                os.path.basename(backup_file_path),
                f.read(),
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        
        # Send email
        email.send(fail_silently=False)
        
        logger.info(f"Daily backup email sent successfully to {settings.ADMIN_EMAIL}")
        
        return f"Backup created and emailed successfully. Records: {total_records}, Size: {file_size_mb:.2f}MB"
        
    except Exception as exc:
        logger.error(f"Daily backup task failed: {str(exc)}")
        raise self.retry(exc=exc)


@shared_task(bind=True, retry_kwargs={'max_retries': 2, 'countdown': 300})
def create_complete_backup_and_email(self):
    """
    Creates complete backup (Excel + Images ZIP) and emails it to admin
    Optional: Can be scheduled weekly or monthly
    """
    try:
        from io import StringIO
        
        logger.info("Starting complete backup task (Database + Images)...")
        
        backup_date = date.today()
        
        # Create complete backup
        output = StringIO()
        call_command('backup_complete', stdout=output)
        output_text = output.getvalue()
        
        # Extract ZIP file path from output
        backup_file_path = None
        if 'Location:' in output_text:
            backup_file_path = output_text.split('Location:')[-1].strip()
        
        if not backup_file_path or not os.path.exists(backup_file_path):
            raise Exception("Complete backup ZIP file not found")
        
        # Get file size
        file_size_mb = os.path.getsize(backup_file_path) / (1024 * 1024)
        
        # Extract stats from output
        total_files = 0
        for line in output_text.split('\n'):
            if 'Media files:' in line:
                try:
                    total_files = int(line.split(':')[1].split('files')[0].strip())
                except:
                    pass
        
        # Prepare email
        subject = f'📦 Complete Backup (Database + Images) - {backup_date.strftime("%B %d, %Y")}'
        
        message = f"""
Complete Backup Created Successfully!

Backup Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 Date: {backup_date.strftime("%B %d, %Y")}
⏰ Time: {datetime.now().strftime("%I:%M %p")}
📊 Database: Included (Excel format)
🖼️ Media Files: {total_files} files
📦 Total Size: {file_size_mb:.2f} MB
📁 File Name: {os.path.basename(backup_file_path)}

This complete backup includes:
✓ All database records (Excel)
✓ Order files and images
✓ Work sample images
✓ News images
✓ All media uploaded today

The ZIP file is attached to this email.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Automated Backup System
Royal Craft Jewelers
        """
        
        # Create email with attachment
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.ADMIN_EMAIL],
        )
        
        # Attach ZIP file
        with open(backup_file_path, 'rb') as f:
            email.attach(
                os.path.basename(backup_file_path),
                f.read(),
                'application/zip'
            )
        
        # Send email
        email.send(fail_silently=False)
        
        logger.info(f"Complete backup email sent successfully to {settings.ADMIN_EMAIL}")
        
        return f"Complete backup created and emailed. Files: {total_files}, Size: {file_size_mb:.2f}MB"
        
    except Exception as exc:
        logger.error(f"Complete backup task failed: {str(exc)}")
        raise self.retry(exc=exc)