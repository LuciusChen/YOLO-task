from typing import List, Optional

from pydantic import BaseModel


class TaskRequest(BaseModel):
    file_path: str
    file_type: str  # "image" or "video"
    target_classes: Optional[List[int]] = None
