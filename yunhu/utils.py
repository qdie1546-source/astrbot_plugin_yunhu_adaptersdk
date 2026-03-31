import hashlib
import hmac
import json

def sign_request(secret: str, data: dict) -> str:
    """生成请求签名（示例：HMAC-SHA256）"""
    message = json.dumps(data, sort_keys=True, separators=(',', ':'))
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def generate_nonce() -> str:
    """生成随机字符串"""
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))