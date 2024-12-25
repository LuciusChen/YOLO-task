from typing import Dict, List, Optional

from pydantic import BaseModel


class TaskRequest(BaseModel):
    file_path: str
    file_type: str  # "image" or "video"
    target_classes: Optional[List[int]] = None
    extra_data: Optional[Dict[str, str]] = None
