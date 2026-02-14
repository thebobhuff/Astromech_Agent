from langchain.tools import tool
from app.core.scheduler import TaskQueue
from app.core.cron import cron_manager

@tool
def add_scheduled_job(name: str, cron_expression: str, task_prompt: str) -> str:
    """
    Creates a recurring cron job that adds a task to the queue based on a schedule.
    
    Args:
        name: Unique name for the job (e.g., "Daily Report").
        cron_expression: 5-part cron string "min hour day month day_of_week"
                         Example: "0 9 * * *" (Every day at 9 AM).
                         Example: "*/30 * * * *" (Every 30 minutes).
        task_prompt: The instruction for the agent when the job triggers (e.g., "Check RSS feed and summarize").
    """
    try:
        job_id = cron_manager.add_job(name, cron_expression, task_prompt)
        return f"Job '{name}' scheduled successfully (ID: {job_id}). Schedule: {cron_expression}"
    except Exception as e:
        return f"Error scheduling job: {e}"

@tool
def list_scheduled_jobs() -> str:
    """Lists all active scheduled cron jobs."""
    try:
        jobs = cron_manager.list_jobs()
        if not jobs:
            return "No scheduled jobs found."
        
        output = ["Running Schedule:"]
        for j in jobs:
            output.append(f"- [{j.cron_expression}] {j.name} (ID: {j.id}): {j.task_prompt}")
        return "\n".join(output)
    except Exception as e:
        return f"Error listing jobs: {e}"

@tool
def remove_scheduled_job(job_id: str) -> str:
    """Removes a scheduled job by its ID."""
    try:
        if cron_manager.remove_job(job_id):
            return f"Job {job_id} removed."
        return "Job not found."
    except Exception as e:
        return f"Error removing job: {e}"

@tool
def add_agent_task(title: str, description: str = "", priority: int = 3) -> str:
    """
    Adds a new task to the agent's background task queue.
    Use this when you need to perform actions later, or break down a large goal into smaller steps.
    
    Args:
        title: Short title of the task.
        description: Detailed instructions for what needs to be done.
        priority: 1 (Low) to 5 (Urgent/High). Default is 3.
    """
    try:
        queue = TaskQueue()
        task = queue.add_task(title, description, priority)
        return f"Task '{title}' added to queue with ID {task.id}."
    except Exception as e:
        return f"Error adding task: {str(e)}"

@tool
def list_pending_tasks() -> str:
    """Lists all currently pending tasks in the queue."""
    try:
        queue = TaskQueue()
        tasks = queue.load_tasks()
        pending = [f"[{t.priority}] {t.title} ({t.id})" for t in tasks if t.status == 'pending']
        if not pending:
            return "No pending tasks."
        return "\n".join(pending)
    except Exception as e:
        return f"Error listing tasks: {str(e)}"

def get_task_tools():
    return [add_agent_task, list_pending_tasks, add_scheduled_job, list_scheduled_jobs, remove_scheduled_job]
