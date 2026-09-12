"""easy_factory — Pydantic 模型工厂，基于字段自动分发到最匹配的模型。"""

from __future__ import annotations

from .exceptions import DispatchFailed, EasyFactoryError
from .factory import BaseModelFactory

__all__ = [
    "BaseModelFactory",
    "DispatchFailed",
    "EasyFactoryError",
]