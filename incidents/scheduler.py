import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django_apscheduler.jobstores import DjangoJobStore

logger = logging.getLogger(__name__)


def run_escalation():
    from django.core.management import call_command
    call_command('escalate_incidents')


def start():
    scheduler = BackgroundScheduler(timezone='Asia/Kolkata')
    scheduler.add_jobstore(DjangoJobStore(), 'default')
    scheduler.add_job(
        run_escalation,
        trigger=IntervalTrigger(hours=1),
        id='escalate_incidents',
        name='Auto-escalate overdue incidents',
        jobstore='default',
        replace_existing=True,
    )
    scheduler.start()
    logger.info('Scheduler started: escalate_incidents runs every hour.')
