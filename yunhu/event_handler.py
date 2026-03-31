import asyncio
import logging
from typing import Dict, List, Callable, Any
from .models import Event

logger = logging.getLogger(__name__)

class EventHandler:
    """事件处理器，管理事件回调"""

    def __init__(self):
        self._handlers: Dict[str, List[Callable[[Event], None]]] = {}

    def register(self, event_type: str, handler: Callable[[Event], None]):
        """注册事件处理器"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug("注册事件处理器: %s", event_type)

    async def emit(self, event_type: str, event: Event):
        """触发事件"""
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.exception("事件处理器出错: %s", e)
        else:
            logger.debug("未注册的事件: %s", event_type)