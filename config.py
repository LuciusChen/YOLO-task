# Configuration for Uvicorn server
UVICORN_HOST = "127.0.0.1"
UVICORN_PORT = 8000

# Configuration for Redis
REDIS_HOST = "localhost"
REDIS_PORT = 6379

# Configuration for OSS
ACCESS_KEY_ID = os.getenv("ACCESS_KEY_ID")
ACCESS_KEY_SECRET = os.getenv("ACCESS_KEY_SECRET")
END_POINT = "http://oss-cn-shanghai.aliyuncs.com/"
BUCKET_NAME = "ossdest-njcjh"
REGION = "cn-shanghai"

# Configuration for Celery
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_SOFT_TIME_LIMIT = 10800

DEFAULT_SAVE_DIR = "output/"
TEMP_DIR = "tmp"

YOLO_MODEL = "yolov8n.pt"
