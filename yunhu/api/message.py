from typing import Dict, Any, Union
from ..models import TextMessage, ImageMessage

async def send_message(
    request_func,
    chat_id: str,
    message: Union[TextMessage, ImageMessage]
) -> Dict[str, Any]:
    """发送消息"""
    payload = {
        "chat_id": chat_id,
        "message": message.dict(exclude_none=True)
    }
    return await request_func("POST", "/message/send", data=payload)

async def recall_message(request_func, message_id: str) -> bool:
    """撤回消息"""
    payload = {"message_id": message_id}
    await request_func("POST", "/message/recall", data=payload)
    return True