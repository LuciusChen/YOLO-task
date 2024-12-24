from celery import chain
from celery.result import AsyncResult
from fastapi import FastAPI, HTTPException
from redis import Redis

from config import REDIS_HOST, REDIS_PORT
from constants import message_translations
from models import TaskRequest
from tasks import celery_app, download_task, process_task, upload_and_cleanup_task

app = FastAPI()


@app.post("/add_task/")
def add_task(task: TaskRequest):
    if not task.file_path:
        raise HTTPException(
            status_code=message_translations["file_not_exist"]["code"],
            detail=message_translations["file_not_exist"]["zh"],
        )

    task_chain = chain(
        download_task.s(task.file_path),
        process_task.s(task.file_type),
        upload_and_cleanup_task.s(),
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
