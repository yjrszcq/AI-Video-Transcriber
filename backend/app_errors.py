from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException


class AppError(Exception):
    """应用内可本地化的错误，包含稳定错误码。"""

    def __init__(self, code: str, message: str, *, status_code: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def error_payload(code: str, message: Optional[str] = None, **extra: Any) -> dict:
    """统一后端错误载荷格式，供前端按 error_code 本地化。"""
    payload = {"error_code": code}
    if message is not None:
        payload["message"] = message
    for key, value in extra.items():
        if value is not None:
            payload[key] = value
    return payload


def http_error(status_code: int, code: str, message: str, **extra: Any) -> HTTPException:
    """构造带标准 detail 结构的 HTTPException。"""
    return HTTPException(
        status_code=status_code,
        detail=error_payload(code, message, **extra),
    )
