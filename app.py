import logging
import subprocess
import time

from celery import chain
from celery.result import AsyncResult
from fastapi import FastAPI, HTTPException
from redis import Redis

from config import REDIS_HOST, REDIS_PORT
from constants import message_translations
from models import TaskRequest
from tasks import (
    celery_app,
    download_task,
    failure_callback,
    process_task,
    success_callback,
    upload_and_cleanup_task,
)

app = FastAPI()


def start_celery():
    subprocess.Popen(["celery", "-A", "tasks", "worker", "--loglevel=info"])


def start_flower():
    subprocess.Popen(["celery", "-A", "tasks", "flower", "--port=5555"])


def check_celery_ready():
    logging.info("Checking if Celery is ready...")
    while True:
        try:
            # Ping the Celery workers
            response = celery_app.control.ping(timeout=1)
            if response:
                logging.info("Celery is ready.")
                break
        except Exception as e:
            logging.error(f"Error checking Celery status: {e}")
        time.sleep(1)  # Wait 1 second before the next check


@app.post("/add_task/")
def add_task(task: TaskRequest):
    if not task.file_path:
        raise HTTPException(
            status_code=message_translations["file_not_exist"]["code"],
            detail=message_translations["file_not_exist"]["zh"],
        )

    task_chain = chain(
        download_task.s(task.dict()),
        process_task.s(),
        upload_and_cleanup_task.s().set(
            link=success_callback.s(),  # 成功回调任务
            link_error=failure_callback.s(),  # 失败回调任务
        ),
    )

    result = task_chain.apply_async()

    return {
        "task_chain_id": result.id,
        "code": message_translations["task_added"]["code"],
        "status": message_translations["task_added"]["zh"],
    }


@app.get("/get_result/{task_id}")
def get_task_result(task_id: str):
    try:
        # 获取 Celery 任务的异步结果
        result = AsyncResult(task_id, app=celery_app)

        # 检查任务状态
        if result.state == "PENDING":
            return {
                "task_id": task_id,
                "code": message_translations["processing"]["code"],
                "status": message_translations["processing"]["zh"],
            }
        elif result.state == "SUCCESS":
            task_result = result.result
            # 检查是否有 "stop_chain" 标记
            if isinstance(task_result, dict) and task_result.get("stop_chain"):
                return {
                    "task_id": task_id,
                    "code": message_translations["no_class_detected"]["code"],
                    "status": message_translations["no_class_detected"]["zh"],
                }
            else:
                return {
                    "task_id": task_id,
                    "code": message_translations["task_success"]["code"],
                    "status": message_translations["task_success"]["zh"],
                    "result": task_result,
                }
        elif result.state == "FAILURE":
            return {
                "task_id": task_id,
                "code": message_translations["internal_error"]["code"],
                "status": message_translations["internal_error"]["zh"],
                "error": str(result.result),
            }
        else:
            return {
                "task_id": task_id,
                "code": message_translations["processing"]["code"],
                "status": result.state,
            }

    except Exception as e:
        raise HTTPException(
            status_code=message_translations["internal_error"]["code"],
            detail=f"{message_translations['internal_error']['zh']}: {e}",
        )
