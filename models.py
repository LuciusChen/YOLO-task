from pydantic import BaseModel


class TaskRequest(BaseModel):
    file_path: str
    file_type: str  # "image" or "video"
