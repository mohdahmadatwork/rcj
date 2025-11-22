# jewelry_orders/celery.py
import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab
# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jewelry_orders.settings')

app = Celery('jewelry_orders')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # Daily database backup at 12:00 AM (midnight)
    'daily-backup-midnight': {
        'task': 'orders.tasks.create_complete_backup_and_email',
        'schedule': crontab(hour=0, minute=0),  # Every day at 00:00
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not executed
        }
    },
    
    # Optional: Complete backup (with images) - Weekly on Sunday at 12:00 AM
    # 'weekly-complete-backup': {
    #     'task': 'orders.tasks.create_complete_backup_and_email',
    #     'schedule': crontab(hour=0, minute=0, day_of_week=0),  # Sunday at 00:00
    #     'options': {
    #         'expires': 7200,  # 2 hours
    #     }
    # },
    
    # Optional: Monthly complete backup - 1st of every month at 12:00 AM
    # 'monthly-complete-backup': {
    #     'task': 'orders.tasks.create_complete_backup_and_email',
    #     'schedule': crontab(hour=0, minute=0, day_of_month=1),
    #     'options': {
    #         'expires': 7200,
    #     }
    # },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
