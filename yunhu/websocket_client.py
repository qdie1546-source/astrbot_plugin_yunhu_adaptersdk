import asyncio
import json
import logging
import websockets
from typing import Optional, Callable, Dict, Any
from .exceptions import YunHuWebSocketError

logger = logging.getLogger(__name__)

class YunHuWebSocketClient:
    """云湖WebSocket客户端"""

    def __init__(
        self,
        url: str,
        app_id: str,
        app_secret: str,
        on_message: Callable[[Dict[str, Any]], None],
        on_error: Optional[Callable[[Exception], None]] = None,
        on_close: Optional[Callable[[], None]] = None
    ):
        self.url = url
        self.app_id = app_id
        self.app_secret = app_secret
        self.on_message = on_message
        self.on_error = on_error or (lambda e: None)
        self.on_close = on_close or (lambda: None)
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def connect(self):
        """建立连接并启动接收循环"""
        try:
            self._ws = await websockets.connect(self.url)
            # 发送认证信息
            auth_payload = {
                "type": "auth",
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            await self._ws.send(json.dumps(auth_payload))
            # 等待认证响应（简化）
            resp = await self._ws.recv()
            data = json.loads(resp)
            if data.get("code") != 0:
                raise YunHuWebSocketError(f"认证失败: {data.get('message')}")
            logger.info("WebSocket连接成功")
            self._running = True
            self._task = asyncio.create_task(self._receive_loop())
        except Exception as e:
            raise YunHuWebSocketError(f"连接失败: {e}") from e

    async def _receive_loop(self):
        """接收消息循环"""
        try:
            while self._running and self._ws:
                message = await self._ws.recv()
                data = json.loads(message)
                await self.on_message(data)
        except websockets.ConnectionClosed as e:
            logger.warning("WebSocket连接关闭: %s", e)
            await self.on_close()
        except Exception as e:
            logger.exception("WebSocket接收错误")
            await self.on_error(e)
        finally:
            await self.close()

    async def close(self):
        """关闭连接"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
            self._ws = None