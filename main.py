import uvicorn

from app import app
from config import UVICORN_HOST, UVICORN_PORT

if __name__ == "__main__":
    uvicorn.run(app, host=UVICORN_HOST, port=UVICORN_PORT)
