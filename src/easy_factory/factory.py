"""
BaseModelFactory — 基于 Pydantic model_validate 的模型分发工厂

核心思路: 注册多个 Pydantic BaseModel 子类, 将原始 dict 数据
按注册顺序尝试 model_validate, 第一个验证成功的即返回。

所有工厂均匹配失败时抛出 DispatchFailed
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ValidationError

from .exceptions import DispatchFailed


class BaseModelFactory:
	
	"""Pydantic 模型工厂，支持注册、优先级和字段匹配分发"""

	__slots__ = ("factories",)

	def __init__(self) -> None:
		self.factories: list[type[BaseModel]] = []

	# ------------------------------------------------------------------
	# 注册
	# ------------------------------------------------------------------

	def register(
		self,
		model: type[BaseModel],
		*,
		priority: int | None = None,
	) -> None:
		
		"""
		注册一个 Pydantic 模型类

		Args:
			model: 要注册的 Pydantic BaseModel 子类
			priority: 插入位置 (0 = 最优先匹配)默认追加到末尾
					  相同优先级: 先注册的优先
		"""
		if model in self.factories:
			return  # 去重

		if priority is None:
			self.factories.append(model)
		else:
			pos = max(0, min(priority, len(self.factories)))
			self.factories.insert(pos, model)

	# ------------------------------------------------------------------
	# 分发
	# ------------------------------------------------------------------

	def dispatcher(self, data: dict[str, Any]) -> BaseModel:
		
		"""
		将 dict 数据分发到第一个匹配的已注册模型

		Args:
			data: 待分发的原始字典数据

		Returns:
			匹配到的 Pydantic 模型实例

		Raises:
			DispatchFailed: 所有注册模型均无法匹配
		"""
		
		for model_cls in self.factories:
			try:
				return model_cls.model_validate(data)
			except ValidationError:
				continue

		raise DispatchFailed(f"无法将数据分发到任何已注册模型: {set(data)}")

	# ------------------------------------------------------------------
	# 便利方法
	# ------------------------------------------------------------------

	def __len__(self) -> int:
		return len(self.factories)

	def __contains__(self, model: type[BaseModel]) -> bool:
		return model in self.factories

	def __repr__(self) -> str:
		names = [t.__name__ for t in self.factories]
		return f"BaseModelFactory({names})"