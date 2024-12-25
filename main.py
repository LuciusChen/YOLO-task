import uvicorn

from app import app, check_celery_ready, start_celery, start_flower
from config import UVICORN_HOST, UVICORN_PORT

if __name__ == "__main__":
    start_celery()
    check_celery_ready()
    start_flower()
    uvicorn.run(app, host=UVICORN_HOST, port=UVICORN_PORT)
