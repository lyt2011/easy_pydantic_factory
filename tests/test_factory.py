"""easy_factory 测试套件 — 覆盖分发正确性、边界情况、异常路径。"""

from __future__ import annotations

from typing import Any, Literal

import pytest
from pydantic import BaseModel, Field

from easy_factory import BaseModelFactory, DispatchFailed, EasyFactoryError


# ======================================================================
# 测试模型
# ======================================================================

class User(BaseModel):
    name: str
    age: int


class Admin(BaseModel):
    name: str
    role: Literal["admin"] = "admin"
    level: int = 1


class Guest(BaseModel):
    name: str
    role: Literal["guest"] = "guest"


class StrictModel(BaseModel):
    model_config = {"extra": "forbid"}
    id: int
    label: str


class OptionalFields(BaseModel):
    a: str = "default_a"
    b: int | None = None


class NestedModel(BaseModel):
    name: str
    child: User


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def factory() -> BaseModelFactory:
    return BaseModelFactory()


# ======================================================================
# 基础分发
# ======================================================================

class TestBasicDispatch:
    """基础分发正确性."""

    def test_simple_dispatch(self, factory: BaseModelFactory) -> None:
        factory.register(User)
        factory.register(Admin)

        result = factory.dispatcher({"name": "Alice", "age": 30})
        assert isinstance(result, User)
        assert result.name == "Alice"
        assert result.age == 30

    def test_dispatch_by_role_field(self, factory: BaseModelFactory) -> None:
        factory.register(User)
        factory.register(Admin)
        factory.register(Guest)

        result = factory.dispatcher({"name": "Bob", "role": "admin"})
        assert isinstance(result, Admin)
        assert result.name == "Bob"
        assert result.role == "admin"

    def test_dispatch_guest(self, factory: BaseModelFactory) -> None:
        factory.register(User)
        factory.register(Admin)
        factory.register(Guest)

        result = factory.dispatcher({"name": "Charlie", "role": "guest"})
        assert isinstance(result, Guest)
        assert result.role == "guest"


# ======================================================================
# DispatchFailed
# ======================================================================

class TestDispatchFailed:
    """DispatchFailed 异常路径."""

    def test_no_models_registered(self, factory: BaseModelFactory) -> None:
        with pytest.raises(DispatchFailed) as exc:
            factory.dispatcher({"name": "x"})
        assert isinstance(exc.value, EasyFactoryError)

    def test_extra_field_rejected(self, factory: BaseModelFactory) -> None:
        factory.register(StrictModel)
        with pytest.raises(DispatchFailed):
            factory.dispatcher({"id": 1, "label": "x", "extra": "boom"})

    def test_missing_required_field(self, factory: BaseModelFactory) -> None:
        factory.register(User)
        with pytest.raises(DispatchFailed):
            factory.dispatcher({"name": "x"})  # missing 'age'

    def test_wrong_type_rejected(self, factory: BaseModelFactory) -> None:
        """静态检查通过但 model_validate 失败."""
        factory.register(User)
        with pytest.raises(DispatchFailed):
            factory.dispatcher({"name": "x", "age": "not-a-number"})

    def test_dispatch_with_defaults(self, factory: BaseModelFactory) -> None:
        """Admin 有默认值, 即使传入数据少也能匹配."""
        factory.register(User)
        factory.register(Admin)
        result = factory.dispatcher({"name": "x"})
        # User 缺 age → skip; Admin 的 role/level 有默认值 → 匹配
        assert isinstance(result, Admin)


# ======================================================================
# 优先级
# ======================================================================

class TestPriority:
    """优先级控制."""

    def test_priority_insertion(self, factory: BaseModelFactory) -> None:
        factory.register(User, priority=0)
        factory.register(Admin, priority=0)

        # Admin 先注册 (priority=0 插入到 0, 排在最前面)
        # 数据 {"name": "x"}:
        #   - Admin: name ✓, role 有默认值, level 有默认值 → 匹配
        #   - User: name ✓, age 缺失 → 跳过
        # → 返回 Admin (因为 Admin 排在前面)
        result = factory.dispatcher({"name": "x"})
        assert isinstance(result, Admin)

    def test_priority_default_append(self, factory: BaseModelFactory) -> None:
        factory.register(Admin)
        factory.register(User)

        # 先注册 Admin, 再注册 User.
        # {"name": "x", "age": 1, "role": "user"}: Admin 拒绝(role != "admin"), User 匹配
        result = factory.dispatcher({"name": "x", "age": 1, "role": "user"})
        assert isinstance(result, User)

    def test_priority_order_matters(self, factory: BaseModelFactory) -> None:
        """两个模型都能匹配同一数据, 优先级决定返回哪个."""
        factory.register(Admin, priority=0)  # 优先
        factory.register(Guest)

        result = factory.dispatcher({"name": "x"})
        assert isinstance(result, Admin)  # Admin 优先, 且 name 足够


# ======================================================================
# 去重
# ======================================================================

class TestDeduplication:
    """注册去重."""

    def test_register_same_model_twice(self, factory: BaseModelFactory) -> None:
        factory.register(User)
        factory.register(User)  # 第二次应该被忽略
        assert len(factory) == 1

    def test_register_priority_dedup(self, factory: BaseModelFactory) -> None:
        factory.register(User, priority=0)
        factory.register(User, priority=5)  # 已存在, 忽略
        assert len(factory) == 1


# ======================================================================
# 边界情况
# ======================================================================

class TestEdgeCases:
    """边界情况."""

    def test_empty_data(self, factory: BaseModelFactory) -> None:
        factory.register(OptionalFields)
        result = factory.dispatcher({})
        assert isinstance(result, OptionalFields)
        assert result.a == "default_a"
        assert result.b is None

    def test_empty_data_no_match(self, factory: BaseModelFactory) -> None:
        factory.register(User)
        with pytest.raises(DispatchFailed):
            factory.dispatcher({})

    def test_empty_factory(self, factory: BaseModelFactory) -> None:
        with pytest.raises(DispatchFailed):
            factory.dispatcher({"anything": 1})

    def test_extra_field_on_strict_model(self, factory: BaseModelFactory) -> None:
        factory.register(StrictModel)
        with pytest.raises(DispatchFailed):
            factory.dispatcher({"id": 1, "label": "x", "extra": "nope"})

    def test_nested_dispatch(self, factory: BaseModelFactory) -> None:
        factory.register(NestedModel)
        result = factory.dispatcher({
            "name": "parent",
            "child": {"name": "child", "age": 5},
        })
        assert isinstance(result, NestedModel)
        assert isinstance(result.child, User)
        assert result.child.name == "child"

    def test_repr(self, factory: BaseModelFactory) -> None:
        factory.register(User)
        factory.register(Admin)
        r = repr(factory)
        assert "User" in r
        assert "Admin" in r

    def test_contains(self, factory: BaseModelFactory) -> None:
        factory.register(User)
        assert User in factory
        assert Admin not in factory


# ======================================================================
# 集成场景: 类 aioclaw Choice.message 分发
# ======================================================================

class TestIntegrationChoiceMessage:
    """模拟 OpenAI / aioverse 的 message 分发场景."""

    class SystemContext(BaseModel):
        role: Literal["system"] = "system"
        content: str

    class UserContext(BaseModel):
        role: Literal["user"] = "user"
        content: str

    class AssistantContext(BaseModel):
        role: Literal["assistant"] = "assistant"
        content: str

    class ToolCallingContext(BaseModel):
        role: Literal["tool_calling"] = "tool_calling"
        content: str = ""
        tool_calls: list[dict[str, Any]] = []

    class ToolOutputContext(BaseModel):
        role: Literal["tool"] = "tool"
        content: str
        tool_call_id: str

    @pytest.fixture
    def choice_factory(self) -> BaseModelFactory:
        f = BaseModelFactory()
        f.register(self.SystemContext)
        f.register(self.UserContext)
        f.register(self.AssistantContext)
        f.register(self.ToolCallingContext)
        f.register(self.ToolOutputContext)
        return f

    def test_dispatch_assistant(self, choice_factory: BaseModelFactory) -> None:
        result = choice_factory.dispatcher({"role": "assistant", "content": "Hello"})
        assert isinstance(result, self.AssistantContext)

    def test_dispatch_tool_calling(self, choice_factory: BaseModelFactory) -> None:
        result = choice_factory.dispatcher({
            "role": "tool_calling",
            "content": "",
            "tool_calls": [{"id": "1", "function": {"name": "f", "arguments": "{}"}}],
        })
        assert isinstance(result, self.ToolCallingContext)

    def test_dispatch_tool_output(self, choice_factory: BaseModelFactory) -> None:
        result = choice_factory.dispatcher({
            "role": "tool",
            "content": "result",
            "tool_call_id": "call_123",
        })
        assert isinstance(result, self.ToolOutputContext)

    def test_dispatch_rejects_unknown_role(self, choice_factory: BaseModelFactory) -> None:
        with pytest.raises(DispatchFailed):
            choice_factory.dispatcher({"role": "unknown_role", "content": "x"})

    def test_dispatch_tool_calling_missing_call_id(self, choice_factory: BaseModelFactory) -> None:
        """ToolCallingContext 不需要 tool_call_id, 应该匹配成功."""
        result = choice_factory.dispatcher({
            "role": "tool_calling",
            "tool_calls": [],
        })
        assert isinstance(result, self.ToolCallingContext)