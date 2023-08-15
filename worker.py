from celery import Celery
from celery.utils.log import get_task_logger
from infrastructure.api_cache import set_data

import redis
from celery import Celery

celery_app = Celery("tasks", broker="redis://redis:6379/0", backend="redis://redis:6379/0")

logger = get_task_logger(__name__)

    
@celery_app.task
def store_key(key, value):
    r = redis.Redis(host="redis", port=6379, db=0)
    r.set(key, value)


@celery_app.task
def retrieve_key(key):
    r = redis.Redis(host="redis", port=6379, db=0)
    return r.get(key)
