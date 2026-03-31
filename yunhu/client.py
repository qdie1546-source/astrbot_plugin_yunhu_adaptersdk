import logging
import asyncio
from typing import Optional, Dict, Any, Callable, Union
import aiohttp
import websockets

from .api import message as message_api, user as user_api
from .models import Message, TextMessage, ImageMessage, UserInfo, Event
from .exceptions import YunHuAuthError, YunHuAPIError, YunHuWebSocketError
from .utils import sign_request
from .websocket_client import YunHuWebSocketClient
from .event_handler import EventHandler

logger = logging.getLogger(__name__)

class YunHuClient:
    """云湖IM 异步客户端（适配 token 查询参数）"""

    def __init__(
        self,
        token: str = None,
        app_id: str = None,
        app_secret: str = None,
        base_url: str = "https://chat-go.jwzhd.com/open-apis/v1",  # 默认云湖API基地址
        websocket_url: str = None,  # 若不需要WebSocket可不传
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.token = token
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = base_url.rstrip('/')
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
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={"User-Agent": "YunHu-SDK/2.0"}
            )

    async def close(self):
        if self._ws_client:
            await self._ws_client.close()
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        retry: bool = True
    ) -> Dict[str, Any]:
        """发送HTTP请求，自动将token加入查询参数"""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        # 合并参数：优先使用传入的params，再添加token
        final_params = params.copy() if params else {}
        if self.token:
            final_params["token"] = self.token
        elif self.app_id and self.app_secret:
            # 备用认证：可自定义
            headers["Authorization"] = f"Bearer {self.app_id}:{self.app_secret}"
        else:
            raise YunHuAuthError("未提供认证信息（token 或 app_id/app_secret）")

        for attempt in range(self.max_retries if retry else 1):
            try:
                async with self._session.request(
                    method, url, json=data, params=final_params, headers=headers
                ) as resp:
                    response = await resp.json()
                    if resp.status == 200:
                        return response
                    elif resp.status == 401:
                        raise YunHuAuthError("认证失败，请检查 token")
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
        """发送消息（适配云湖 /bot/send）"""
        if isinstance(message, str):
            message = TextMessage(text=message)

        endpoint = "/bot/send"
        # 云湖要求 token 在查询参数中，已在 _request 自动添加，故 params 可不传
        data = {
            "chat_id": chat_id,
            "message": message.dict(exclude_none=True)
        }
        return await self._request("POST", endpoint, data=data)

    async def recall_message(self, message_id: str) -> bool:
        """撤回消息（需根据实际API实现）"""
        # 假设有 /message/recall 接口
        endpoint = "/message/recall"
        data = {"message_id": message_id}
        await self._request("POST", endpoint, data=data)
        return True

    # ========== 用户 API ==========
    async def get_user_info(self, user_id: str) -> UserInfo:
        """获取用户信息（需根据实际API实现）"""
        endpoint = f"/user/{user_id}"
        data = await self._request("GET", endpoint)
        return UserInfo(**data)

    # ========== 事件 API ==========
    def on(self, event_type: str, handler: Callable[[Event], None]):
        self._event_handler.register(event_type, handler)

    async def start_event_stream(self):
        """启动WebSocket事件流（可选）"""
        if not self.websocket_url:
            logger.warning("未提供 websocket_url，无法启动事件流")
            return
        if self._running:
            return
        self._running = True

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