import asyncio
import base64
import os
import pickle
import shutil
import sys
import tempfile
from collections import defaultdict
from io import BytesIO
from pathlib import Path

import aiohttp
import cv2
import numpy as np
import oss2
from fastapi import HTTPException
from redis import Redis
from ultralytics import YOLO
from ultralytics.utils.files import increment_path
from ultralytics.utils.plotting import Annotator, colors

from config import (
    ACCESS_KEY_ID,
    ACCESS_KEY_SECRET,
    BUCKET_NAME,
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    CELERY_SOFT_TIME_LIMIT,
    DEFAULT_SAVE_DIR,
    END_POINT,
    REGION,
    TEMP_DIR,
)
from constants import message_translations
from utils import convert_numpy_types, increment_path

redis_conn = Redis(decode_responses=True)
model = YOLO("yolov8n.pt")
auth = oss2.Auth(ACCESS_KEY_ID, ACCESS_KEY_SECRET)
bucket = oss2.Bucket(auth, END_POINT, BUCKET_NAME, region=REGION)

from celery import Celery

# 初始化 Celery 实例
celery_app = Celery("tasks", broker=CELERY_BROKER_URL)

# 配置 Celery
celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    result_backend=CELERY_RESULT_BACKEND,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(bind=True, soft_time_limit=CELERY_SOFT_TIME_LIMIT)
def download_task(self, file_path: str) -> str:
    local_file_path = download_file_from_oss(file_path)
    return local_file_path


@celery_app.task(bind=True, soft_time_limit=CELERY_SOFT_TIME_LIMIT)
def process_task(
    self, local_file_path: str, file_type: str, target_classes=None
) -> dict:
    result = process_yolo_task(
        local_file_path, file_type, target_classes=target_classes
    )

    if result.get("class_counts"):
        return result
    else:
        result["stop_chain"] = "True"
        return result


@celery_app.task(bind=True, soft_time_limit=CELERY_SOFT_TIME_LIMIT)
def upload_and_cleanup_task(self, result: dict) -> dict:
    try:
        output_file_path = result["output_file_path"]
        local_file_path = result["local_file_path"]

        if "stop_chain" not in result:
            oss_key = upload_file_to_oss(output_file_path)
            result["oss_key"] = oss_key

        cleanup_files(local_file_path, output_file_path)
        return result
    except Exception as e:
        print(f"Error during upload and cleanup: {e}")
        raise


def cleanup_files(local_file_path: str, output_file_path: str) -> None:
    os.remove(local_file_path)
    shutil.rmtree(os.path.dirname(output_file_path))


def download_file_from_oss(file_path: str) -> str:
    local_file_path = os.path.join(TEMP_DIR, os.path.basename(file_path))
    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

    oss2.resumable_download(
        bucket,
        file_path,
        local_file_path,
        store=oss2.ResumableDownloadStore(root="/tmp"),
        multiget_threshold=100 * 1024,
        part_size=100 * 1024,
        num_threads=4,
    )

    return local_file_path


def upload_file_to_oss(file_path: str) -> str:
    oss_key = f"output/{os.path.basename(file_path)}"
    oss2.resumable_upload(
        bucket,
        oss_key,
        file_path,
        store=oss2.ResumableStore(root="/tmp"),
        multipart_threshold=100 * 1024,
        part_size=100 * 1024,
        num_threads=4,
    )
    return oss_key


def process_yolo_task(
    local_file_path: str,
    file_type: str,
    save_dir: str = DEFAULT_SAVE_DIR,
    target_classes: list = [],
) -> dict:
    if file_type.lower() == "image":
        return process_image_task(local_file_path, save_dir, target_classes)
    elif file_type.lower() == "video":
        return process_video_task(local_file_path, save_dir, target_classes)
    else:
        return {"error": message_translations["unsupported_file_type"]["zh"]}


def process_image_task(image_path: str, save_dir: str, target_classes=None) -> dict:
    try:
        image = cv2.imread(image_path)
        if image is None:
            return {"error": f"无法读取图片 {image_path}"}

        image_name = Path(image_path).stem
        detection = model.predict(
            image,
            save=True,
            project=str(save_dir),
            name=image_name,
            classes=target_classes,
        )
        detections = detection[0]

        if hasattr(detections, "boxes") and hasattr(detections.boxes, "cls"):
            classes = detections.boxes.cls.cpu().numpy().astype(int)
        else:
            return {"error": message_translations["no_class_detected"]["zh"]}

        names = model.model.names
        class_counts = count_classes(classes, names)

        results_dir = Path(save_dir) / image_name
        generated_file_path = results_dir / "image0.jpg"
        output_file_path = results_dir / f"{image_name}.jpg"
        if generated_file_path.exists():
            generated_file_path.rename(output_file_path)

        return {
            "class_counts": class_counts,
            "local_file_path": str(image_path),
            "output_file_path": str(output_file_path),
        }

    except Exception as e:
        return {"error": str(e)}


def count_classes(classes: np.ndarray, names: dict) -> dict:
    class_counts = {}
    for cls in classes:
        class_name = names[cls]
        class_counts[class_name] = class_counts.get(class_name, 0) + 1
    return class_counts


def process_video_task(video_path: str, save_dir: str, target_classes=None) -> dict:
    try:
        track_history = set()
        counting_region = {
            "name": "YOLOv8 Full Frame Region",
            "counts": defaultdict(int),
            "region_color": (255, 42, 4),
            "text_color": (255, 255, 255),
        }

        device = model.device.type
        model.to("cuda") if device == "cuda" else model.to("cpu")

        names = model.model.names
        videocapture = cv2.VideoCapture(video_path)
        frame_width, frame_height = int(videocapture.get(3)), int(videocapture.get(4))
        fps, fourcc = int(videocapture.get(5)), cv2.VideoWriter_fourcc(*"mp4v")

        save_dir = increment_path(Path(save_dir) / "exp", exist_ok=False)
        save_dir.mkdir(parents=True, exist_ok=True)
        video_writer_path = save_dir / f"{Path(video_path).stem}.mp4"
        video_writer = cv2.VideoWriter(
            str(video_writer_path),
            fourcc,
            fps,
            (frame_width, frame_height),
        )

        while videocapture.isOpened():
            success, frame = videocapture.read()
            if not success:
                break

            results = model.track(frame, persist=True, classes=target_classes)

            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu()
                track_ids = results[0].boxes.id.int().cpu().tolist()
                clss = results[0].boxes.cls.cpu().tolist()

                annotator = Annotator(frame, line_width=2, example=str(names))

                for box, track_id, cls in zip(boxes, track_ids, clss):
                    label = f"{track_id}: {names[cls]}"
                    annotator.box_label(box, label, color=colors(cls, True))

                    if track_id not in track_history:
                        track_history.add(track_id)
                        counting_region["counts"][names[cls]] += 1

            region_label = ", ".join(
                [f"{cls}: {count}" for cls, count in counting_region["counts"].items()]
            )
            region_color = counting_region["region_color"]
            region_text_color = counting_region["text_color"]

            text_size, _ = cv2.getTextSize(
                region_label, cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.7, thickness=2
            )
            text_x = 10
            text_y = 30
            cv2.rectangle(
                frame,
                (text_x - 5, text_y - text_size[1] - 5),
                (text_x + text_size[0] + 5, text_y + 5),
                region_color,
                -1,
            )
            cv2.putText(
                frame,
                region_label,
                (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                region_text_color,
                2,
            )

            video_writer.write(frame)

        video_writer.release()
        videocapture.release()

        return {
            "class_counts": dict(counting_region["counts"]),
            "local_file_path": str(video_path),
            "output_file_path": str(video_writer_path),
        }

    except Exception as e:
        return {"error": str(e)}
