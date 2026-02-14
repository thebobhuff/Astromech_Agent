from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging
from app.memory.rag import get_vector_memory
from app.memory.short_term import ShortTermMemoryManager
from datetime import timedelta

logger = logging.getLogger(__name__)

def setup_cron_jobs():
    scheduler = BackgroundScheduler()

    # Schedule memory cleanup
    scheduler.add_job(
        id='cleanup_old_memories_job',
        func=cleanup_old_memories_task,
        trigger=IntervalTrigger(days=1),  # Run once every day
        start_date=datetime.now(),
        name="Cleanup old long-term memories"
    )
    
    # Schedule short-term memory cleanup (every 30 minutes)
    scheduler.add_job(
        id='cleanup_short_term_memories_job',
        func=cleanup_short_term_memories_task,
        trigger=IntervalTrigger(minutes=30), # Run every 30 minutes
        start_date=datetime.now(),
        name="Cleanup short-term memories older than 2 hours"
    )
    
    # Add other cron jobs here if needed
    # scheduler.add_job(...)

    scheduler.start()
    logger.info("Cron jobs scheduler started.")

def cleanup_old_memories_task():
    logger.info("Executing scheduled task: cleanup_old_memories_task")
    vector_memory = get_vector_memory()
    vector_memory.cleanup_old_memories(older_than_days=30) # Clean up memories older than 30 days
    logger.info("Completed scheduled task: cleanup_old_memories_task")

def cleanup_short_term_memories_task():
    logger.info("Executing scheduled task: cleanup_short_term_memories_task")
    st_memory_manager = ShortTermMemoryManager()
    # Clean up short-term memories older than 2 hours
    st_memory_manager.cleanup_expired(older_than_timedelta=timedelta(hours=2))
    logger.info("Completed scheduled task: cleanup_short_term_memories_task")
