"""easy_factory 异常定义"""

from __future__ import annotations


class EasyFactoryError(Exception):
	
	"""easy_factory 基础异常"""
	...


class DispatchFailed(EasyFactoryError):
	
	"""所有已注册模型均无法匹配传入数据时抛出"""
	...