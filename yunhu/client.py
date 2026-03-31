import logging
import asyncio
from typing import Optional, Dict, Any, Callable, Union
import aiohttp
import websockets

from .models import TextMessage, ImageMessage, UserInfo, Event
from .exceptions import YunHuAuthError, YunHuAPIError
from .websocket_client import YunHuWebSocketClient
from .event_handler import EventHandler

logger = logging.getLogger(__name__)

class YunHuClient:
    """云湖IM 异步客户端（适配 token 查询参数）"""

    def __init__(
        self,
        token: str = None,
        base_url: str = "https://chat-go.jwzhd.com/open-apis/v1",
        websocket_url: str = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.token = token
        self.base_url = base_url.rstrip('/')
        self.websocket_url = websocket_url
        self.timeout = timeout
        self.max_retries = max_retries

        self._session: Optional[aiohttp.ClientSession] = None
        self._ws_client = None
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
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        # 将 token 加入查询参数
        final_params = params.copy() if params else {}
        if self.token:
            final_params["token"] = self.token
        else:
            raise YunHuAuthError("未提供 token")

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

    async def send_message(self, chat_id: str, message: Union[str, TextMessage, ImageMessage]) -> Dict[str, Any]:
        """发送消息（适配 /bot/send）"""
        if isinstance(message, str):
            message = TextMessage(text=message)

        endpoint = "/bot/send"
        data = {
            "chat_id": chat_id,
            "message": message.dict(exclude_none=True)
        }
        return await self._request("POST", endpoint, data=data)

    # 其他方法（如 get_user_info）可根据需要添加

    def on(self, event_type: str, handler: Callable[[Event], None]):
        self._event_handler.register(event_type, handler)

    async def start_event_stream(self):
        if not self.websocket_url:
            logger.warning("未提供 websocket_url，无法启动事件流")
            return
        # ... 实现省略，按需添加