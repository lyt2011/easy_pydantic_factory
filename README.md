# easy_factory

基于 Pydantic `model_fields` 的模型分发工厂。注册多个 Pydantic 模型后, 将原始 dict 数据自动分发到最匹配的模型, 适用于消息/事件按字段自动路由到对应结构体的场景。

## 安装

```bash
pip install /path/to/easy-factory/
```

需要 Python >= 3.11, pydantic >= 2.0。

## 快速开始

```python
from typing import Literal

from pydantic import BaseModel

from easy_factory import BaseModelFactory, DispatchFailed


class User(BaseModel):
    name: str
    age: int


class Admin(BaseModel):
    name: str
    role: Literal["admin"] = "admin"
    level: int = 1


factory = BaseModelFactory()
factory.register(User)
factory.register(Admin)

result = factory.dispatcher({"name": "Bob", "role": "admin"})
assert isinstance(result, Admin)
```

## 匹配规则

分发时依次尝试每个已注册模型, 第一个满足以下全部条件的模型胜出:

1. 数据的字段不能超出模型声明的字段 (extra field 检查);
2. 模型所有 required 字段都存在于数据中;
3. `model_validate(data)` 校验成功。

所有模型均匹配失败时抛出 `DispatchFailed`。

## API

### `BaseModelFactory()`

模型工厂实例。

- `register(model, *, priority: int | None = None)` — 注册一个 Pydantic 模型类。
  `priority` 为插入位置 (0 = 最优先匹配, 默认追加到末尾); 相同优先级先注册的先匹配; 重复注册同一模型会被忽略。
- `dispatcher(data: dict) -> BaseModel` — 将 dict 数据分发到第一个匹配的模型, 失败抛 `DispatchFailed`。
- `len(factory)` — 已注册模型数量。
- `model in factory` — 判断模型是否已注册。

### 异常

- `EasyFactoryError` — 基础异常。
- `DispatchFailed(EasyFactoryError)` — 所有已注册模型均无法匹配传入数据时抛出。

## 运行测试

```bash
pip install pytest
pytest tests/
```

## 完整示例

以 `role` 字段分发多种消息上下文, 类似 OpenAI message 的结构体派发:

```python
from typing import Any, Literal

from pydantic import BaseModel

from easy_factory import BaseModelFactory


class SystemContext(BaseModel):
    role: Literal["system"] = "system"
    content: str


class ToolCallingContext(BaseModel):
    role: Literal["tool_calling"] = "tool_calling"
    content: str = ""
    tool_calls: list[dict[str, Any]] = []


class ToolOutputContext(BaseModel):
    role: Literal["tool"] = "tool"
    content: str
    tool_call_id: str


factory = BaseModelFactory()
factory.register(SystemContext)
factory.register(ToolCallingContext)
factory.register(ToolOutputContext)

msg1 = factory.dispatcher({"role": "system", "content": "hi"})
msg2 = factory.dispatcher({
    "role": "tool_calling",
    "tool_calls": [{"id": "1", "function": {"name": "f", "arguments": "{}"}}],
})
msg3 = factory.dispatcher({"role": "tool", "content": "ok", "tool_call_id": "call_1"})
```