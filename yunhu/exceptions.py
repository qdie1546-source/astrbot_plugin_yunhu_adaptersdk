class YunHuError(Exception):
    """SDK基础异常"""
    pass

class YunHuAuthError(YunHuError):
    """认证错误"""
    pass

class YunHuAPIError(YunHuError):
    """API调用错误"""
    def __init__(self, message: str, code: int = None, response: dict = None):
        super().__init__(message)
        self.code = code
        self.response = response

class YunHuConnectionError(YunHuError):
    """连接错误"""
    pass

class YunHuWebSocketError(YunHuError):
    """WebSocket错误"""
    pass