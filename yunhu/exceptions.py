class YunHuError(Exception):
    pass

class YunHuAuthError(YunHuError):
    pass

class YunHuAPIError(YunHuError):
    def __init__(self, message: str, code: int = None, response: dict = None):
        super().__init__(message)
        self.code = code
        self.response = response