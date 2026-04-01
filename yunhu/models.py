from pydantic import BaseModel
from typing import Optional

class TextMessage(BaseModel):
    type: str = "text"
    text: str

class ImageMessage(BaseModel):
    type: str = "image"
    url: str
    width: Optional[int] = None
    height: Optional[int] = None

class AtMessage(BaseModel):
    type: str = "at"
    user_id: str