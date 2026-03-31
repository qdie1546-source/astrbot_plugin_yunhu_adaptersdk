from typing import Dict, Any

async def get_user_info(request_func, user_id: str) -> Dict[str, Any]:
    """获取用户信息"""
    return await request_func("GET", f"/user/{user_id}")