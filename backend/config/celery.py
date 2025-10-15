import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("ringsync")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "check-alarms-every-minute": {
        "task": "core.tasks.check_and_trigger_alarms",
        "schedule": crontab(minute="*"),
    },
}
