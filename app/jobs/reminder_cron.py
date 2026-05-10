import asyncio
import logging
import pytz

from apscheduler.schedulers.background import (
    BackgroundScheduler
)

from apscheduler.jobstores.sqlalchemy import (
    SQLAlchemyJobStore
)

from app.database import SessionLocal

from app.config import settings

from app.services.growth_service import (
    flag_missed_patients
)

from app.services.reminder_service import (
    send_due_reminders
)


# =====================================================
# LOGGER
# =====================================================

logger = logging.getLogger(__name__)


# =====================================================
# TIMEZONE
# =====================================================

IST = pytz.timezone("Asia/Kolkata")


# =====================================================
# PREVENT DUPLICATE SCHEDULERS
# =====================================================

_scheduler = None


# =====================================================
# DAILY JOB WRAPPER
# =====================================================

def run_daily_jobs():
    """
    APScheduler entry point.

    Creates a dedicated asyncio event loop
    so async WhatsApp/message sending works
    properly inside scheduler threads.
    """

    db = SessionLocal()

    try:

        # ---------------------------------------------
        # CREATE EVENT LOOP
        # ---------------------------------------------

        loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)

        # ---------------------------------------------
        # RUN ASYNC JOBS
        # ---------------------------------------------

        loop.run_until_complete(
            _async_daily_jobs(db)
        )

    except Exception as e:

        logger.error(
            f"❌ Daily scheduler wrapper failed: {e}"
        )

    finally:

        db.close()

        try:

            loop.close()

        except Exception:
            pass


# =====================================================
# ASYNC DAILY JOBS
# =====================================================

async def _async_daily_jobs(db):
    """
    Runs every day at 9:30 AM IST.

    Automated Tasks:
    1. Flags missed patients
    2. Sends due reminders
    """

    try:

        from app.models.clinic import Clinic

        clinics = db.query(Clinic).all()

        logger.info(
            f"🏥 Starting daily jobs "
            f"for {len(clinics)} clinics"
        )

        # ---------------------------------------------
        # PROCESS EACH CLINIC
        # ---------------------------------------------

        for clinic in clinics:

            logger.info(
                f"\n🏥 Processing clinic: "
                f"{clinic.name}"
            )

            try:

                # =====================================
                # 1. FLAG MISSED PATIENTS
                # =====================================

                missed = flag_missed_patients(
                    db,
                    clinic.id
                )

                logger.info(
                    f"📋 {missed} patients "
                    f"flagged as missed"
                )

                # =====================================
                # 2. SEND REMINDERS
                # =====================================

                result = await send_due_reminders(
                    db,
                    clinic.id
                )

                logger.info(
                    f"📱 {result['sent']} "
                    f"reminders sent"
                )

                logger.info(
                    f"❌ {result['failed']} "
                    f"reminders failed"
                )

            except Exception as clinic_error:

                logger.error(

                    f"❌ Error processing clinic "
                    f"{clinic.name}: {clinic_error}"
                )

        logger.info(
            "✅ Daily jobs completed successfully"
        )

    except Exception as e:

        logger.error(
            f"❌ Async daily scheduler failed: {e}"
        )


# =====================================================
# START SCHEDULER
# =====================================================

def start_scheduler():
    """
    Starts APScheduler with:
    - Persistent PostgreSQL jobs
    - IST timezone support
    - Restart-safe scheduling
    """

    global _scheduler

    # -------------------------------------------------
    # PREVENT DUPLICATE SCHEDULERS
    # -------------------------------------------------

    if _scheduler is not None:

        logger.info(
            "⚠️ Scheduler already running — skipping"
        )

        return _scheduler

    try:

        # =============================================
        # PERSISTENT JOB STORE
        # =============================================

        jobstores = {

            "default": SQLAlchemyJobStore(
                url=settings.DATABASE_URL
            )
        }

        # =============================================
        # CREATE SCHEDULER
        # =============================================

        _scheduler = BackgroundScheduler(

            jobstores=jobstores,

            timezone=IST
        )

        # =============================================
        # DAILY JOB
        # =============================================

        _scheduler.add_job(

            func=run_daily_jobs,

            trigger="cron",

            hour=9,

            minute=30,

            id="daily_clinic_jobs",

            name="Daily Clinic Reminder Jobs",

            replace_existing=True,

            misfire_grace_time=3600
        )

        # =============================================
        # START SCHEDULER
        # =============================================

        _scheduler.start()

        logger.info(
            "✅ Scheduler started "
            "— runs daily at 9:30 AM IST"
        )

        return _scheduler

    except Exception as e:

        logger.error(
            f"❌ Failed to start scheduler: {e}"
        )

        raise