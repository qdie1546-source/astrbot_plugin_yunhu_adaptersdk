from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

class BaseMessage(BaseModel):
    """消息基类"""
    type: str

class TextMessage(BaseMessage):
    """文本消息"""
    type: str = "text"
    text: str

class ImageMessage(BaseMessage):
    """图片消息"""
    type: str = "image"
    url: str
    width: Optional[int] = None
    height: Optional[int] = None

class AtMessage(BaseMessage):
    """@消息"""
    type: str = "at"
    user_id: str
    name: Optional[str] = None

class Message(BaseModel):
    """完整消息模型"""
    id: str
    chat_id: str
    sender_id: str
    sender_name: str
    content: Union[TextMessage, ImageMessage, AtMessage, List[BaseMessage]]
    timestamp: int
    is_group: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        # 根据content中的type解析具体消息类型
        content = data.get("content")
        if isinstance(content, dict):
            msg_type = content.get("type")
            if msg_type == "text":
                content_obj = TextMessage(**content)
            elif msg_type == "image":
                content_obj = ImageMessage(**content)
            elif msg_type == "at":
                content_obj = AtMessage(**content)
            else:
                content_obj = BaseMessage(**content)
        else:
            content_obj = content
        data["content"] = content_obj
        return cls(**data)

class UserInfo(BaseModel):
    """用户信息"""
    id: str
    name: str
    avatar: Optional[str] = None
    is_bot: bool = False

class Event(BaseModel):
    """事件基类"""
    type: str
    data: Dict[str, Any]

class MessageEvent(Event):
    """消息事件"""
    type: str = "message"
    message: Message