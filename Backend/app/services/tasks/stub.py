import logging
import uuid

logger = logging.getLogger(__name__)


async def enqueue_background_task(task_name: str, payload: dict) -> str:
    """Placeholder seam for the future task queue (Celery/RQ/arq) that
    will run forecast retraining and image-classification processing
    out of the request path, per the spec. Not wired into any route
    yet — logs and returns a fake task id so calling code has a stable
    interface to develop against before the real queue exists.
    """
    task_id = str(uuid.uuid4())
    logger.info("enqueue_background_task stub: task=%s id=%s", task_name, task_id)
    return task_id
