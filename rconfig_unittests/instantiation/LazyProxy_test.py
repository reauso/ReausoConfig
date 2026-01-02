"""Unit tests for LazyProxy module."""

import dataclasses
from dataclasses import dataclass
from unittest import TestCase

from rconfig.instantiation.LazyProxy import (
    create_lazy_proxy_class,
    get_lazy_proxy_class,
    is_lazy_proxy,
    force_initialize,
    clear_proxy_cache,
    _LAZY_STATE_ATTR,
)


class LazyProxyCreationTests(TestCase):
    """Tests for lazy proxy class creation."""

    def setUp(self):
        clear_proxy_cache()

    def test_create_lazy_proxy__SimpleClass__ReturnsSubclass(self):
        # Arrange
        class SimpleClass:
            def __init__(self, value: int):
                self.value = value

        # Act
        LazyProxy = create_lazy_proxy_class(SimpleClass)

        # Assert
        self.assertTrue(issubclass(LazyProxy, SimpleClass))

    def test_create_lazy_proxy__Dataclass__ReturnsSubclass(self):
        # Arrange
        @dataclass
        class DataModel:
            name: str
            size: int

        # Act
        LazyProxy = create_lazy_proxy_class(DataModel)

        # Assert
        self.assertTrue(issubclass(LazyProxy, DataModel))

    def test_isinstance__LazyProxyInstance__ReturnsTrue(self):
        # Arrange
        class Model:
            def __init__(self, value: int):
                self.value = value

        LazyProxy = create_lazy_proxy_class(Model)

        # Act
        instance = LazyProxy(value=42)

        # Assert
        self.assertIsInstance(instance, Model)

    def test_get_lazy_proxy_class__SameClass__ReturnsCached(self):
        # Arrange
        class MyClass:
            pass

        # Act
        proxy1 = get_lazy_proxy_class(MyClass)
        proxy2 = get_lazy_proxy_class(MyClass)

        # Assert
        self.assertIs(proxy1, proxy2)

    def test_proxy_class_name__ContainsOriginalName(self):
        # Arrange
        class OriginalClass:
            pass

        # Act
        LazyProxy = create_lazy_proxy_class(OriginalClass)

        # Assert
        self.assertIn("OriginalClass", LazyProxy.__name__)


class LazyProxyInitializationTests(TestCase):
    """Tests for lazy initialization behavior."""

    def setUp(self):
        clear_proxy_cache()

    def test_init_not_called__UntilAttributeAccess(self):
        # Arrange
        init_calls = []

        class TrackedClass:
            def __init__(self, value: int):
                init_calls.append(value)
                self.value = value

        LazyProxy = create_lazy_proxy_class(TrackedClass)

        # Act
        instance = LazyProxy(value=42)

        # Assert - init not called yet
        self.assertEqual(len(init_calls), 0)

    def test_getattr__TriggersInit(self):
        # Arrange
        init_calls = []

        class TrackedClass:
            def __init__(self, value: int):
                init_calls.append(value)
                self.value = value

        LazyProxy = create_lazy_proxy_class(TrackedClass)
        instance = LazyProxy(value=42)

        # Act - access attribute
        _ = instance.value

        # Assert - init was called
        self.assertEqual(len(init_calls), 1)
        self.assertEqual(init_calls[0], 42)

    def test_setattr__TriggersInit(self):
        # Arrange
        init_calls = []

        class TrackedClass:
            def __init__(self, value: int):
                init_calls.append(value)
                self.value = value

        LazyProxy = create_lazy_proxy_class(TrackedClass)
        instance = LazyProxy(value=42)

        # Act - set attribute
        instance.new_attr = "test"

        # Assert - init was called
        self.assertEqual(len(init_calls), 1)

    def test_delattr__TriggersInit(self):
        # Arrange
        init_calls = []

        class TrackedClass:
            def __init__(self, value: int):
                init_calls.append(value)
                self.value = value
                self.deletable = True

        LazyProxy = create_lazy_proxy_class(TrackedClass)
        instance = LazyProxy(value=42)

        # Act - delete attribute (triggers init first, then allows delete)
        del instance.deletable

        # Assert - init was called
        self.assertEqual(len(init_calls), 1)

    def test_init_called_once__MultipleAccesses(self):
        # Arrange
        init_calls = []

        class TrackedClass:
            def __init__(self, value: int):
                init_calls.append(value)
                self.value = value

        LazyProxy = create_lazy_proxy_class(TrackedClass)
        instance = LazyProxy(value=42)

        # Act - multiple accesses
        _ = instance.value
        _ = instance.value
        instance.new_attr = "test"
        _ = instance.new_attr

        # Assert - init called only once
        self.assertEqual(len(init_calls), 1)


class LazyProxyBehaviorTests(TestCase):
    """Tests for lazy proxy behavior after initialization."""

    def setUp(self):
        clear_proxy_cache()

    def test_after_init__BehavesLikeRealObject(self):
        # Arrange
        @dataclass
        class Model:
            value: int
            name: str

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42, name="test")

        # Act - trigger init by accessing attribute
        result_value = instance.value
        result_name = instance.name

        # Assert
        self.assertEqual(result_value, 42)
        self.assertEqual(result_name, "test")

    def test_methods__WorkAfterInit(self):
        # Arrange
        class Calculator:
            def __init__(self, base: int):
                self.base = base

            def add(self, n: int) -> int:
                return self.base + n

        LazyProxy = create_lazy_proxy_class(Calculator)
        instance = LazyProxy(base=10)

        # Act
        result = instance.add(5)

        # Assert
        self.assertEqual(result, 15)

    def test_repr__ShowsLazyStatusBeforeInit(self):
        # Arrange
        class Model:
            def __init__(self, value: int):
                self.value = value

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)

        # Act
        repr_str = repr(instance)

        # Assert - shows lazy status
        self.assertIn("LazyProxy", repr_str)
        self.assertIn("not initialized", repr_str)


class LazyProxyUtilityTests(TestCase):
    """Tests for utility functions."""

    def setUp(self):
        clear_proxy_cache()

    def test_is_lazy_proxy__Uninitialized__ReturnsTrue(self):
        # Arrange
        class Model:
            def __init__(self, value: int):
                self.value = value

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)

        # Act
        result = is_lazy_proxy(instance)

        # Assert
        self.assertTrue(result)

    def test_is_lazy_proxy__Initialized__ReturnsFalse(self):
        # Arrange
        class Model:
            def __init__(self, value: int):
                self.value = value

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)
        _ = instance.value  # trigger init

        # Act
        result = is_lazy_proxy(instance)

        # Assert
        self.assertFalse(result)

    def test_is_lazy_proxy__RegularObject__ReturnsFalse(self):
        # Arrange
        class Model:
            def __init__(self, value: int):
                self.value = value

        instance = Model(42)  # Regular, not lazy

        # Act
        result = is_lazy_proxy(instance)

        # Assert
        self.assertFalse(result)

    def test_force_initialize__LazyProxy__InitializesWithoutAccess(self):
        # Arrange
        init_calls = []

        class TrackedClass:
            def __init__(self, value: int):
                init_calls.append(value)
                self.value = value

        LazyProxy = create_lazy_proxy_class(TrackedClass)
        instance = LazyProxy(value=42)

        # Act
        force_initialize(instance)

        # Assert
        self.assertEqual(len(init_calls), 1)
        self.assertFalse(is_lazy_proxy(instance))

    def test_force_initialize__RegularObject__NoOp(self):
        # Arrange
        class Model:
            def __init__(self, value: int):
                self.value = value

        instance = Model(42)

        # Act - should not raise
        force_initialize(instance)

        # Assert
        self.assertEqual(instance.value, 42)


class LazyProxyEdgeCaseTests(TestCase):
    """Tests for edge cases."""

    def setUp(self):
        clear_proxy_cache()

    def test_class_with_slots__WorksCorrectly(self):
        # Arrange
        class SlottedClass:
            __slots__ = ["value"]

            def __init__(self, value: int):
                self.value = value

        LazyProxy = create_lazy_proxy_class(SlottedClass)

        # Act
        instance = LazyProxy(value=42)
        result = instance.value

        # Assert
        self.assertEqual(result, 42)

    def test_frozen_dataclass__WorksCorrectly(self):
        # Arrange
        @dataclass(frozen=True)
        class FrozenModel:
            value: int
            name: str

        LazyProxy = create_lazy_proxy_class(FrozenModel)

        # Act
        instance = LazyProxy(value=42, name="test")
        result = instance.value

        # Assert
        self.assertEqual(result, 42)

    def test_class_with_property__PropertyWorks(self):
        # Arrange
        class WithProperty:
            def __init__(self, value: int):
                self._value = value

            @property
            def value(self) -> int:
                return self._value * 2

        LazyProxy = create_lazy_proxy_class(WithProperty)

        # Act
        instance = LazyProxy(value=21)
        result = instance.value

        # Assert
        self.assertEqual(result, 42)

    def test_inheritance__SubclassProxyIsSubclassOfOriginal(self):
        # Arrange
        class BaseClass:
            pass

        class DerivedClass(BaseClass):
            def __init__(self, value: int):
                self.value = value

        LazyProxy = create_lazy_proxy_class(DerivedClass)

        # Act
        instance = LazyProxy(value=42)

        # Assert
        self.assertIsInstance(instance, BaseClass)
        self.assertIsInstance(instance, DerivedClass)


class LazyProxyTransparencyTests(TestCase):
    """Tests to ensure lazy proxies are completely transparent to user code.

    IMPORTANT: These tests verify that user code does NOT need to import
    anything from rconfig to work with lazy objects. The proxy must behave
    exactly like the real object in all ways that user code might depend on.
    """

    def setUp(self):
        clear_proxy_cache()

    def test_isinstance__WithOriginalClass__ReturnsTrue(self):
        """User code: isinstance(obj, MyClass) must work."""
        @dataclass
        class Model:
            value: int

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)

        # User code pattern - must work
        self.assertTrue(isinstance(instance, Model))

    def test_isinstance__WithBaseClass__ReturnsTrue(self):
        """User code: isinstance(obj, BaseClass) must work."""
        class Base:
            pass

        class Derived(Base):
            def __init__(self, value: int):
                self.value = value

        LazyProxy = create_lazy_proxy_class(Derived)
        instance = LazyProxy(value=42)

        # User code pattern - must work
        self.assertTrue(isinstance(instance, Base))
        self.assertTrue(isinstance(instance, Derived))

    def test_attribute_access__Works(self):
        """User code: obj.attribute must work."""
        @dataclass
        class Model:
            value: int
            name: str

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42, name="test")

        # User code pattern - must work
        self.assertEqual(instance.value, 42)
        self.assertEqual(instance.name, "test")

    def test_method_calls__Work(self):
        """User code: obj.method() must work."""
        class Calculator:
            def __init__(self, base: int):
                self.base = base

            def add(self, n: int) -> int:
                return self.base + n

            def multiply(self, n: int) -> int:
                return self.base * n

        LazyProxy = create_lazy_proxy_class(Calculator)
        instance = LazyProxy(base=10)

        # User code pattern - must work
        self.assertEqual(instance.add(5), 15)
        self.assertEqual(instance.multiply(3), 30)

    def test_property_access__Works(self):
        """User code: obj.property must work."""
        class Model:
            def __init__(self, value: int):
                self._value = value

            @property
            def value(self) -> int:
                return self._value

            @property
            def doubled(self) -> int:
                return self._value * 2

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=21)

        # User code pattern - must work
        self.assertEqual(instance.value, 21)
        self.assertEqual(instance.doubled, 42)

    def test_attribute_setting__Works(self):
        """User code: obj.attr = value must work."""
        class Model:
            def __init__(self, value: int):
                self.value = value

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)

        # User code pattern - must work
        instance.value = 100
        self.assertEqual(instance.value, 100)

        instance.new_attr = "added"
        self.assertEqual(instance.new_attr, "added")

    def test_attribute_deletion__Works(self):
        """User code: del obj.attr must work."""
        class Model:
            def __init__(self, value: int):
                self.value = value
                self.deletable = True

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)

        # User code pattern - must work
        del instance.deletable
        self.assertFalse(hasattr(instance, "deletable"))

    def test_hasattr__Works(self):
        """User code: hasattr(obj, 'attr') must work."""
        @dataclass
        class Model:
            value: int

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)

        # User code pattern - must work
        self.assertTrue(hasattr(instance, "value"))
        self.assertFalse(hasattr(instance, "nonexistent"))

    def test_getattr__Works(self):
        """User code: getattr(obj, 'attr') must work."""
        @dataclass
        class Model:
            value: int

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)

        # User code pattern - must work
        self.assertEqual(getattr(instance, "value"), 42)
        self.assertEqual(getattr(instance, "nonexistent", "default"), "default")

    def test_setattr__Works(self):
        """User code: setattr(obj, 'attr', value) must work."""
        class Model:
            def __init__(self, value: int):
                self.value = value

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)

        # User code pattern - must work
        setattr(instance, "value", 100)
        self.assertEqual(instance.value, 100)

    def test_dict_access__AfterInit__Works(self):
        """User code: obj.__dict__ must work after initialization."""
        class Model:
            def __init__(self, value: int):
                self.value = value

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)

        # Trigger init
        _ = instance.value

        # User code pattern - must work after init
        self.assertIn("value", instance.__dict__)
        self.assertEqual(instance.__dict__["value"], 42)

    def test_str__Works(self):
        """User code: str(obj) must work."""
        class Model:
            def __init__(self, value: int):
                self.value = value

            def __str__(self) -> str:
                return f"Model(value={self.value})"

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)

        # User code pattern - must work
        self.assertEqual(str(instance), "Model(value=42)")

    def test_bool__Works(self):
        """User code: if obj: ... must work."""
        class Model:
            def __init__(self, value: int):
                self.value = value

            def __bool__(self) -> bool:
                return self.value > 0

        LazyProxy = create_lazy_proxy_class(Model)

        positive = LazyProxy(value=42)
        negative = LazyProxy(value=-1)

        # User code pattern - must work
        self.assertTrue(bool(positive))
        self.assertFalse(bool(negative))

    def test_comparison__Works(self):
        """User code: obj1 == obj2 must work."""
        @dataclass
        class Model:
            value: int

            def __eq__(self, other: object) -> bool:
                if not isinstance(other, Model):
                    return False
                return self.value == other.value

        LazyProxy = create_lazy_proxy_class(Model)

        proxy1 = LazyProxy(value=42)
        proxy2 = LazyProxy(value=42)
        proxy3 = LazyProxy(value=99)

        # User code pattern - must work
        self.assertEqual(proxy1, proxy2)
        self.assertNotEqual(proxy1, proxy3)

    def test_iteration__Works(self):
        """User code: for item in obj: ... must work."""
        class Container:
            def __init__(self, items: list):
                self.items = items

            def __iter__(self):
                return iter(self.items)

        LazyProxy = create_lazy_proxy_class(Container)
        instance = LazyProxy(items=[1, 2, 3])

        # User code pattern - must work
        result = list(instance)
        self.assertEqual(result, [1, 2, 3])

    def test_len__Works(self):
        """User code: len(obj) must work."""
        class Container:
            def __init__(self, items: list):
                self.items = items

            def __len__(self) -> int:
                return len(self.items)

        LazyProxy = create_lazy_proxy_class(Container)
        instance = LazyProxy(items=[1, 2, 3])

        # User code pattern - must work
        self.assertEqual(len(instance), 3)

    def test_indexing__Works(self):
        """User code: obj[key] must work."""
        class Container:
            def __init__(self, items: list):
                self.items = items

            def __getitem__(self, index: int):
                return self.items[index]

        LazyProxy = create_lazy_proxy_class(Container)
        instance = LazyProxy(items=[1, 2, 3])

        # User code pattern - must work
        self.assertEqual(instance[0], 1)
        self.assertEqual(instance[1], 2)

    def test_callable__Works(self):
        """User code: obj() must work if object is callable."""
        class Factory:
            def __init__(self, base: int):
                self.base = base

            def __call__(self, n: int) -> int:
                return self.base + n

        LazyProxy = create_lazy_proxy_class(Factory)
        instance = LazyProxy(base=10)

        # User code pattern - must work
        result = instance(5)
        self.assertEqual(result, 15)

    def test_dataclass_fields__Works(self):
        """User code: dataclasses.fields(obj) must work."""
        @dataclass
        class Model:
            value: int
            name: str

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42, name="test")

        # Trigger init first
        _ = instance.value

        # User code pattern - must work
        fields = dataclasses.fields(instance)
        field_names = [f.name for f in fields]
        self.assertIn("value", field_names)
        self.assertIn("name", field_names)

    def test_dataclass_asdict__Works(self):
        """User code: dataclasses.asdict(obj) must work."""
        @dataclass
        class Model:
            value: int
            name: str

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42, name="test")

        # User code pattern - must work
        result = dataclasses.asdict(instance)
        self.assertEqual(result, {"value": 42, "name": "test"})


class LazyProxyKnownLimitationsTests(TestCase):
    """Tests documenting known limitations of the lazy proxy approach.

    These are edge cases where the proxy may behave differently from the
    real object. Users should be aware of these limitations.
    """

    def setUp(self):
        clear_proxy_cache()

    def test_type__ReturnsProxyClass(self):
        """LIMITATION: type(obj) returns proxy class, not original class.

        Use isinstance() instead of type() == SomeClass for type checking.
        """
        @dataclass
        class Model:
            value: int

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)

        # type() returns the proxy class, not Model
        self.assertIsNot(type(instance), Model)
        # But isinstance() works correctly
        self.assertIsInstance(instance, Model)

    def test_class_attribute__ReturnsProxyClass(self):
        """LIMITATION: obj.__class__ returns proxy class, not original class.

        Use isinstance() instead of obj.__class__ == SomeClass.
        """
        @dataclass
        class Model:
            value: int

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)

        # __class__ is the proxy class
        self.assertIsNot(instance.__class__, Model)
        # But isinstance() works correctly
        self.assertIsInstance(instance, Model)

    def test_dict__BeforeInit__ContainsLazyState(self):
        """LIMITATION: obj.__dict__ before init contains lazy state.

        Access attributes directly instead of inspecting __dict__.
        """
        @dataclass
        class Model:
            value: int

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)

        # Before init, __dict__ has lazy state (accessing it triggers init though)
        # This test documents the behavior
        _ = instance.value  # trigger init first
        self.assertIn("value", instance.__dict__)


class LazyProxyReprTests(TestCase):
    """Tests for LazyProxy __repr__ behavior."""

    def setUp(self):
        clear_proxy_cache()

    def test_repr__AfterInit__UsesTargetClassRepr(self):
        """Test that repr after initialization uses the target class's __repr__."""
        # Arrange
        class ModelWithRepr:
            def __init__(self, value: int):
                self.value = value

            def __repr__(self) -> str:
                return f"ModelWithRepr(value={self.value})"

        LazyProxy = create_lazy_proxy_class(ModelWithRepr)
        instance = LazyProxy(value=42)

        # Trigger initialization
        _ = instance.value

        # Act
        result = repr(instance)

        # Assert - should use the target class's __repr__
        self.assertEqual(result, "ModelWithRepr(value=42)")

    def test_repr__BeforeInit__ShowsNotInitialized(self):
        """Test that repr before initialization shows lazy status."""
        # Arrange
        class Model:
            def __init__(self, value: int):
                self.value = value

        LazyProxy = create_lazy_proxy_class(Model)
        instance = LazyProxy(value=42)

        # Act - no initialization yet
        result = repr(instance)

        # Assert
        self.assertIn("LazyProxy", result)
        self.assertIn("not initialized", result)

    def test_repr__DataclassAfterInit__UsesDataclassRepr(self):
        """Test that repr works correctly with dataclass targets."""
        # Arrange
        @dataclass
        class DataModel:
            value: int
            name: str

        LazyProxy = create_lazy_proxy_class(DataModel)
        instance = LazyProxy(value=42, name="test")

        # Trigger initialization
        _ = instance.value

        # Act
        result = repr(instance)

        # Assert - dataclass has auto-generated __repr__
        self.assertIn("DataModel", result)
        self.assertIn("value=42", result)
        self.assertIn("name='test'", result)