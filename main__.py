from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from celery_tasks import store_key
from celery import group
import redis

from celery import Celery

celery_app = Celery("tasks", broker="redis://redis:6379/0", backend="redis://redis:6379/0")


app = FastAPI(title="WMS Demo",
              description="Demo using FastAPI and MapScript to serve OGC WMS",
              version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@celery_app.task
def process_items(items):
    split_items = [item.split() for item in items]
    group_result = group(store_key.s(item[0], item[1].upper()) for item in split_items)()
    return group_result.join()


@app.post("/process")
async def process_items_endpoint(items: list):
    task = process_items.delay(items)
    return {"message": "Task to process items submitted", "task_id": task.id}


