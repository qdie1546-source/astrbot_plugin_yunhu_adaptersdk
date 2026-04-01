import logging
import asyncio
import aiohttp
from typing import Optional, Dict, Any, Union
from .models import TextMessage, ImageMessage
from .exceptions import YunHuAuthError, YunHuAPIError

logger = logging.getLogger(__name__)

class YunHuClient:
    """云湖IM异步客户端"""

    def __init__(
        self,
        token: Optional[str] = None,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        base_url: str = "https://chat-go.jwzhd.com/open-apis/v1",
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.token = token
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def start(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={"User-Agent": "YunHu-SDK/2.0"}
            )

    async def close(self):
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
        final_params = params.copy() if params else {}

        # 认证方式：优先使用 token，否则使用 app_id+app_secret
        if self.token:
            final_params["token"] = self.token
        elif self.app_id and self.app_secret:
            # 如果有 app_id+app_secret，可以按需实现签名等
            final_params["app_id"] = self.app_id
            final_params["app_secret"] = self.app_secret
        else:
            raise YunHuAuthError("未提供认证信息（token 或 app_id+app_secret）")

        for attempt in range(self.max_retries if retry else 1):
            try:
                async with self._session.request(
                    method, url, json=data, params=final_params, headers=headers
                ) as resp:
                    response = await resp.json()
                    if resp.status == 200:
                        return response
                    elif resp.status == 401:
                        raise YunHuAuthError("认证失败，请检查 token 或 app_id+app_secret")
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
        """发送消息"""
        if isinstance(message, str):
            message = TextMessage(text=message)
        endpoint = "/bot/send"
        data = {
            "chat_id": chat_id,
            "message": message.dict(exclude_none=True)
        }
        return await self._request("POST", endpoint, data=data)