import uvicorn

from app import app, start_celery
from config import UVICORN_HOST, UVICORN_PORT

if __name__ == "__main__":
    start_celery()
    uvicorn.run(app, host=UVICORN_HOST, port=UVICORN_PORT)
