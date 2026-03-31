import logging
import asyncio
from typing import Optional, Dict, Any, Callable, Union
import aiohttp
import websockets

from .api import message as message_api, user as user_api, event as event_api
from .models import Message, TextMessage, ImageMessage, UserInfo, Event
from .exceptions import YunHuAuthError, YunHuAPIError, YunHuWebSocketError
from .utils import sign_request
from .websocket_client import YunHuWebSocketClient
from .event_handler import EventHandler

logger = logging.getLogger(__name__)

class YunHuClient:
    """云湖IM 异步客户端"""

    def __init__(
        self,
        token: str = None,                     # 新增 token 参数
        app_id: str = None,
        app_secret: str = None,
        base_url: str = "https://api.yhchat.com/v1",
        websocket_url: str = "wss://ws.yhchat.com/v1",
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.token = token
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = base_url
        self.websocket_url = websocket_url
        self.timeout = timeout
        self.max_retries = max_retries

        self._session: Optional[aiohttp.ClientSession] = None
        self._ws_client: Optional[YunHuWebSocketClient] = None
        self._event_handler = EventHandler()
        self._running = False

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """初始化HTTP会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={"User-Agent": "YunHu-SDK/2.0"}
            )

    async def close(self):
        """关闭连接"""
        if self._ws_client:
            await self._ws_client.close()
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get_auth_headers(self) -> Dict[str, str]:
        """生成认证头"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        elif self.app_id and self.app_secret:
            # 可根据实际认证方式修改，这里假设使用 Bearer token 拼接
            return {"Authorization": f"Bearer {self.app_id}:{self.app_secret}"}
        else:
            raise YunHuAuthError("未提供认证信息（token 或 app_id/app_secret）")

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        retry: bool = True
    ) -> Dict[str, Any]:
        """发送HTTP请求，自动添加认证头"""
        url = f"{self.base_url}{endpoint}"
        headers = await self._get_auth_headers()
        headers["Content-Type"] = "application/json"

        # 可选签名（若需要）
        if data and self.app_secret:
            headers["X-Sign"] = sign_request(self.app_secret, data)

        for attempt in range(self.max_retries if retry else 1):
            try:
                async with self._session.request(
                    method, url, json=data, params=params, headers=headers
                ) as resp:
                    response = await resp.json()
                    if resp.status == 200:
                        return response
                    elif resp.status == 401:
                        raise YunHuAuthError("认证失败，请检查 token 或 app_id/app_secret")
                    else:
                        raise YunHuAPIError(
                            f"API错误: {resp.status} - {response.get('message', '未知错误')}",
                            code=resp.status,
                            response=response
                        )
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == self.max_retries - 1:
                    raise YunHuAPIError(f"网络请求失败: {e}") from e
                await asyncio.sleep(2 ** attempt)

    # ========== 消息 API ==========
    async def send_message(
        self,
        chat_id: str,
        message: Union[str, TextMessage, ImageMessage]
    ) -> Dict[str, Any]:
        """发送消息"""
        if isinstance(message, str):
            message = TextMessage(text=message)
        return await message_api.send_message(self._request, chat_id, message)

    async def recall_message(self, message_id: str) -> bool:
        """撤回消息"""
        return await message_api.recall_message(self._request, message_id)

    # ========== 用户 API ==========
    async def get_user_info(self, user_id: str) -> UserInfo:
        """获取用户信息"""
        data = await user_api.get_user_info(self._request, user_id)
        return UserInfo(**data)

    # ========== 事件 API ==========
    def on(self, event_type: str, handler: Callable[[Event], None]):
        """注册事件处理器"""
        self._event_handler.register(event_type, handler)

    async def start_event_stream(self):
        """启动WebSocket事件流"""
        if self._running:
            logger.warning("事件流已在运行")
            return
        self._running = True

        # WebSocket 认证需要根据实际情况传递 token 或 app_id
        auth_data = {}
        if self.token:
            auth_data = {"token": self.token}
        elif self.app_id and self.app_secret:
            auth_data = {"app_id": self.app_id, "app_secret": self.app_secret}
        else:
            raise YunHuAuthError("无法启动 WebSocket：缺少认证信息")

        self._ws_client = YunHuWebSocketClient(
            url=self.websocket_url,
            auth_data=auth_data,
            on_message=self._on_ws_message,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close
        )
        await self._ws_client.connect()

    async def _on_ws_message(self, data: Dict[str, Any]):
        """处理WebSocket接收到的消息"""
        event_type = data.get("type")
        if event_type:
            event = Event(**data)
            await self._event_handler.emit(event_type, event)
        else:
            logger.debug("收到未知格式的消息: %s", data)

    async def _on_ws_error(self, exc: Exception):
        logger.error("WebSocket错误: %s", exc)

    async def _on_ws_close(self):
        logger.info("WebSocket连接已关闭")
        self._running = False