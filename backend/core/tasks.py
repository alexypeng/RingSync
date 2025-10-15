from celery import shared_task
from django.utils import timezone
from datetime import datetime
from .models import Alarm, AlarmLog


@shared_task
def check_and_trigger_alarms():
    """Check for alarms that should trigger now"""
    now = timezone.now()
    current_time = now.time()
    current_day = now.weekday()

    active_alarms = Alarm.objects.filter(is_active=True)

    for alarm in active_alarms:
        if should_trigger_alarm(alarm, current_time, current_day):
            trigger_alarm.delay(alarm.id)


def should_trigger_alarm(alarm, time, day):
    """Check if the alarm should be triggered"""
    alarm_hour = alarm.time.hour
    alarm_minute = alarm.time.minute

    if time.hour != alarm_hour or time.minute != alarm_minute:
        return False

    days = alarm.days_of_week.split(",")
    if str(day) not in days:
        return False

    return True


@shared_task
def trigger_alarm(alarm_id):
    """Trigger alarm for all group members"""
    from .models import Alarm, AlarmLog

    try:
        alarm = Alarm.objects.get(id=alarm_id)
    except Alarm.DoesNotExist:
        return

    members = alarm.group.members.all()

    for member in members:
        log = AlarmLog.objects.create(
            alarm=alarm,
            user=member,
            call_status="pending",
        )

        make_call_to_user.delay(log.id, member.phone_number)


@shared_task
def make_call_to_user(alarm_log_id, phone_number):
    """Placeholder"""
    from .models import AlarmLog

    try:
        log = AlarmLog.objects.get(id=alarm_log_id)
        log.call_status = "completed"
        log.save()
    except AlarmLog.DoesNotExist:
        pass
