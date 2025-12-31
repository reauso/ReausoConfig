from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Union
from unittest.case import TestCase
from unittest.mock import MagicMock, patch

from rconfig.ConfigStore import ConfigStore
from rconfig.ConfigValidator import ConfigValidator
from rconfig.ConfigInstantiator import ConfigInstantiator
from rconfig.errors import (
    AmbiguousTargetError,
    InstantiationError,
    MissingFieldError,
    TargetNotFoundError,
)


class ConfigInstantiatorTests(TestCase):
    def _empty_store(self) -> ConfigStore:
        store = ConfigStore()
        store._known_references.clear()
        return store

    def _create_instantiator(self, store: ConfigStore) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__SimpleDataclass__ReturnsInstance(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            hidden_size: int
            dropout: float = 0.1

        store.register("model", Model)
        instantiator = self._create_instantiator(store)
        config = {"_target_": "model", "hidden_size": 256}

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, Model)
        self.assertEqual(result.hidden_size, 256)
        self.assertEqual(result.dropout, 0.1)

    def test_instantiate__AllFieldsProvided__UsesProvidedValues(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            size: int
            name: str
            enabled: bool

        store.register("model", Model)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "model",
            "size": 100,
            "name": "test",
            "enabled": True,
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertEqual(result.size, 100)
        self.assertEqual(result.name, "test")
        self.assertTrue(result.enabled)

    def test_instantiate__NestedConfig__InstantiatesRecursively(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class InnerModel:
            value: int

        @dataclass
        class OuterModel:
            inner: InnerModel
            name: str

        store.register("inner", InnerModel)
        store.register("outer", OuterModel)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer",
            "inner": {"_target_": "inner", "value": 42},
            "name": "test",
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, OuterModel)
        self.assertIsInstance(result.inner, InnerModel)
        self.assertEqual(result.inner.value, 42)
        self.assertEqual(result.name, "test")

    def test_instantiate__DeeplyNestedConfig__InstantiatesAllLevels(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Level3:
            value: int

        @dataclass
        class Level2:
            level3: Level3

        @dataclass
        class Level1:
            level2: Level2

        store.register("l3", Level3)
        store.register("l2", Level2)
        store.register("l1", Level1)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "l1",
            "level2": {
                "_target_": "l2",
                "level3": {"_target_": "l3", "value": 99},
            },
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, Level1)
        self.assertIsInstance(result.level2, Level2)
        self.assertIsInstance(result.level2.level3, Level3)
        self.assertEqual(result.level2.level3.value, 99)

    def test_instantiate__ListOfNestedConfigs__InstantiatesAll(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Item:
            value: int

        @dataclass
        class Container:
            items: list

        store.register("item", Item)
        store.register("container", Container)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "container",
            "items": [
                {"_target_": "item", "value": 1},
                {"_target_": "item", "value": 2},
                {"_target_": "item", "value": 3},
            ],
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, Container)
        self.assertEqual(len(result.items), 3)
        for i, item in enumerate(result.items, 1):
            self.assertIsInstance(item, Item)
            self.assertEqual(item.value, i)

    def test_instantiate__InvalidConfig__RaisesValidationError(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            required: int

        store.register("model", Model)
        instantiator = self._create_instantiator(store)
        config = {"_target_": "model"}  # Missing required field

        # Act & Assert
        with self.assertRaises(MissingFieldError):
            instantiator.instantiate(config)

    def test_instantiate__UnknownTarget__RaisesTargetNotFoundError(self):
        # Arrange
        store = self._empty_store()
        instantiator = self._create_instantiator(store)
        config = {"_target_": "unknown"}

        # Act & Assert
        with self.assertRaises(TargetNotFoundError):
            instantiator.instantiate(config)

    def test_instantiate__ConstructorFails__RaisesInstantiationError(self):
        # Arrange
        store = self._empty_store()

        class FailingClass:
            def __init__(self, value: int):
                raise ValueError("Intentional failure")

        store.register("failing", FailingClass)
        instantiator = self._create_instantiator(store)
        config = {"_target_": "failing", "value": 42}

        # Act & Assert
        with self.assertRaises(InstantiationError) as context:
            instantiator.instantiate(config)

        self.assertEqual(context.exception.target, "failing")
        self.assertIn("Intentional failure", context.exception.reason)

    def test_instantiate__WithValidateFalse__SkipsValidation(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            value: int

        store.register("model", Model)
        instantiator = self._create_instantiator(store)
        # Missing required field but validation disabled
        config = {"_target_": "model"}

        # Act & Assert
        # Should raise InstantiationError (from constructor) not validation error
        with self.assertRaises(InstantiationError):
            instantiator.instantiate(config, validate=False)

    def test_instantiate__OptionalField__AcceptsNone(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            value: Optional[int]

        store.register("model", Model)
        instantiator = self._create_instantiator(store)
        config = {"_target_": "model", "value": None}

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsNone(result.value)

    def test_instantiate__RegularClass__WorksWithNonDataclass(self):
        # Arrange
        store = self._empty_store()

        class RegularClass:
            def __init__(self, x: int, y: str):
                self.x = x
                self.y = y

        store.register("regular", RegularClass)
        instantiator = self._create_instantiator(store)
        config = {"_target_": "regular", "x": 10, "y": "hello"}

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, RegularClass)
        self.assertEqual(result.x, 10)
        self.assertEqual(result.y, "hello")

    def test_instantiate__DictInConfig__PreservedAsDict(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            params: dict

        store.register("model", Model)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "model",
            "params": {"a": 1, "b": 2},
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertEqual(result.params, {"a": 1, "b": 2})

    def test_instantiate__NestedConfigInDict__InstantiatesNested(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            mapping: dict

        store.register("inner", Inner)
        store.register("outer", Outer)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer",
            "mapping": {
                "first": {"_target_": "inner", "value": 1},
                "second": {"_target_": "inner", "value": 2},
            },
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result.mapping["first"], Inner)
        self.assertIsInstance(result.mapping["second"], Inner)
        self.assertEqual(result.mapping["first"].value, 1)
        self.assertEqual(result.mapping["second"].value, 2)


class ConfigInstantiatorImplicitTargetTests(TestCase):
    """Tests for instantiation with implicit _target_ inference."""

    def _empty_store(self) -> ConfigStore:
        store = ConfigStore()
        store._known_references.clear()
        return store

    def _create_instantiator(self, store: ConfigStore) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__ImplicitNestedConfig__ReturnsCorrectInstance(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            inner: Inner
            name: str

        store.register("inner", Inner)
        store.register("outer", Outer)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer",
            "inner": {"value": 42},
            "name": "test",
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, Outer)
        self.assertIsInstance(result.inner, Inner)
        self.assertEqual(result.inner.value, 42)
        self.assertEqual(result.name, "test")

    def test_instantiate__DeeplyNestedImplicit__ReturnsCorrectInstance(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Level3:
            value: int

        @dataclass
        class Level2:
            level3: Level3

        @dataclass
        class Level1:
            level2: Level2

        store.register("l3", Level3)
        store.register("l2", Level2)
        store.register("l1", Level1)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "l1",
            "level2": {
                "level3": {"value": 99},
            },
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, Level1)
        self.assertIsInstance(result.level2, Level2)
        self.assertIsInstance(result.level2.level3, Level3)
        self.assertEqual(result.level2.level3.value, 99)

    def test_instantiate__MixedExplicitImplicit__ReturnsCorrectInstance(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class A:
            x: int

        @dataclass
        class B:
            y: str

        @dataclass
        class Container:
            a: A
            b: B

        store.register("a", A)
        store.register("b", B)
        store.register("container", Container)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "container",
            "a": {"x": 10},
            "b": {"_target_": "b", "y": "hello"},
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertEqual(result.a.x, 10)
        self.assertEqual(result.b.y, "hello")

    def test_instantiate__OptionalField_ImplicitNested__ReturnsCorrectInstance(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            inner: Optional[Inner]

        store.register("inner", Inner)
        store.register("outer", Outer)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer",
            "inner": {"value": 42},
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result.inner, Inner)
        self.assertEqual(result.inner.value, 42)


class ConfigInstantiatorEdgeCaseTests(TestCase):
    """Tests for edge cases and uncovered code paths in ConfigInstantiator."""

    def _empty_store(self) -> ConfigStore:
        store = ConfigStore()
        store._known_references.clear()
        return store

    def _create_instantiator(self, store: ConfigStore) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__BrokenTypeHints__FallsBackGracefully(self):
        """Test that get_type_hints failure is handled gracefully (lines 82-83)."""
        store = self._empty_store()

        class BrokenAnnotations:
            def __init__(self, value: "NonExistentType") -> None:  # noqa: F821
                self.value = value

        store.register("broken", BrokenAnnotations)
        instantiator = self._create_instantiator(store)
        config = {"_target_": "broken", "value": 42}

        # Mock get_type_hints to raise an exception
        with patch(
            "rconfig.ConfigInstantiator.get_type_hints",
            side_effect=NameError("name 'NonExistentType' is not defined"),
        ):
            result = instantiator.instantiate(config, validate=False)

        self.assertIsInstance(result, BrokenAnnotations)
        self.assertEqual(result.value, 42)

    def test_instantiate__AbstractType_ImplicitNested__RaisesAmbiguousError(self):
        """Test that abstract types can't be implicitly inferred (line 236)."""
        store = self._empty_store()

        class AbstractBase(ABC):
            @abstractmethod
            def method(self) -> None:
                pass

        class Concrete(AbstractBase):
            def __init__(self, value: int) -> None:
                self.value = value

            def method(self) -> None:
                pass

        @dataclass
        class Container:
            item: AbstractBase

        store.register("concrete", Concrete)
        store.register("container", Container)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "container",
            "item": {"value": 10},  # Implicit - but AbstractBase is abstract
        }

        with self.assertRaises(AmbiguousTargetError):
            instantiator.instantiate(config)

    def test_instantiate__MultipleSubclasses_ImplicitNested__RaisesAmbiguousError(self):
        """Test that ambiguous types fail during instantiation (line 245)."""
        store = self._empty_store()

        class Base:
            def __init__(self, value: int) -> None:
                self.value = value

        class ChildA(Base):
            pass

        class ChildB(Base):
            pass

        @dataclass
        class Container:
            item: Base

        store.register("base", Base)
        store.register("child_a", ChildA)
        store.register("child_b", ChildB)
        store.register("container", Container)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "container",
            "item": {"value": 10},  # Implicit - but Base has multiple subclasses
        }

        with self.assertRaises(AmbiguousTargetError):
            instantiator.instantiate(config)

    def test_instantiate__NoTypeHint__ProcessesWithoutInference(self):
        """Test field without type hint is processed without inference (line 207)."""
        store = self._empty_store()

        class Model:
            def __init__(self, data) -> None:  # No type hint
                self.data = data

        store.register("model", Model)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "model",
            "data": {"key": "value"},  # Dict stays as dict
        }

        result = instantiator.instantiate(config, validate=False)

        self.assertEqual(result.data, {"key": "value"})

    def test_instantiate__UnionWithMultipleTypes__SkipsImplicitInference(self):
        """Test Union[A, B] doesn't trigger implicit inference (line 189)."""
        store = self._empty_store()

        @dataclass
        class TypeA:
            value: int

        @dataclass
        class TypeB:
            name: str

        @dataclass
        class Container:
            item: Union[TypeA, TypeB]

        store.register("type_a", TypeA)
        store.register("type_b", TypeB)
        store.register("container", Container)
        instantiator = self._create_instantiator(store)
        # Dict without _target_ - stays as dict because Union can't be inferred
        config = {
            "_target_": "container",
            "item": {"value": 10},  # Will stay as dict
        }

        result = instantiator.instantiate(config, validate=False)

        # Item stays as dict since Union[A, B] can't be inferred
        self.assertIsInstance(result.item, dict)
        self.assertEqual(result.item, {"value": 10})

    def test_instantiate__NotRegisteredType_ImplicitNested__StaysAsDict(self):
        """Test dict when expected type not registered stays as dict (line 217)."""
        store = self._empty_store()

        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            inner: Inner  # Inner is NOT registered

        # Only register Outer, not Inner
        store.register("outer", Outer)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer",
            "inner": {"value": 42},  # Can't infer because Inner not registered
        }

        result = instantiator.instantiate(config, validate=False)

        # Inner stays as dict since it couldn't be inferred
        self.assertIsInstance(result.inner, dict)

    def test_instantiate__GenericTypeHint__SkipsImplicitInference(self):
        """Test generic types like list[X] don't trigger implicit inference (line 149)."""
        store = self._empty_store()

        @dataclass
        class Item:
            value: int

        @dataclass
        class Container:
            items: list[Item]  # Generic type

        store.register("item", Item)
        store.register("container", Container)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "container",
            "items": [{"value": 1}, {"value": 2}],  # Dicts stay as dicts
        }

        result = instantiator.instantiate(config, validate=False)

        # Items stay as dicts since list[Item] can't trigger implicit inference
        self.assertIsInstance(result.items[0], dict)

    def test_instantiate__ExplicitNestedInDict__InstantiatesCorrectly(self):
        """Test explicit nested configs in dicts are instantiated."""
        store = self._empty_store()

        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            mapping: dict

        store.register("inner", Inner)
        store.register("outer", Outer)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer",
            "mapping": {
                "item1": {"_target_": "inner", "value": 1},  # Explicit _target_
                "item2": {"no_target": "stays_dict"},
            },
        }

        result = instantiator.instantiate(config)

        self.assertIsInstance(result.mapping["item1"], Inner)
        self.assertIsInstance(result.mapping["item2"], dict)

    def test_instantiate__DictHasTargetKey__NotTreatedAsImplicit(self):
        """Test dict with _target_ key is explicit, not implicit (line 205)."""
        store = self._empty_store()

        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            inner: Inner

        store.register("inner", Inner)
        store.register("outer", Outer)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer",
            "inner": {"_target_": "inner", "value": 42},  # Explicit _target_
        }

        result = instantiator.instantiate(config)

        self.assertIsInstance(result.inner, Inner)
        self.assertEqual(result.inner.value, 42)


class ConfigInstantiatorHelperMethodTests(TestCase):
    """Tests for helper methods to improve coverage (lines 149, 153, 226-227, 236, 259)."""

    def _empty_store(self) -> ConfigStore:
        store = ConfigStore()
        store._known_references.clear()
        return store

    def _create_instantiator(self, store: ConfigStore) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    # --- _is_class_type tests (lines 148-149, 152-153) ---
    def test_isClassType__GenericType__ReturnsFalse(self):
        """Test generic types return False (line 148-149)."""
        store = self._empty_store()
        instantiator = self._create_instantiator(store)

        # Generic types have origin, should return False
        self.assertFalse(instantiator._is_class_type(list[int]))
        self.assertFalse(instantiator._is_class_type(dict[str, int]))
        self.assertFalse(instantiator._is_class_type(Optional[int]))

    def test_isClassType__NonTypeObject__ReturnsFalse(self):
        """Test non-type objects return False (line 152-153)."""
        store = self._empty_store()
        instantiator = self._create_instantiator(store)

        # Non-type objects should return False
        self.assertFalse(instantiator._is_class_type("not a type"))  # type: ignore
        self.assertFalse(instantiator._is_class_type(42))  # type: ignore
        self.assertFalse(instantiator._is_class_type(None))  # type: ignore

    # --- _find_registered_subclasses TypeError handling (lines 226-227) ---
    def test_findSubclasses__IssubclassTypeError__HandledGracefully(self):
        """Test TypeError in issubclass is handled (lines 226-227)."""
        store = self._empty_store()

        class Base:
            pass

        store.register("base", Base)
        instantiator = self._create_instantiator(store)

        # Mock issubclass to raise TypeError
        with patch(
            "rconfig.ConfigInstantiator.issubclass",
            side_effect=TypeError("Mock TypeError"),
        ):
            result = instantiator._find_registered_subclasses(Base)

        self.assertIsInstance(result, list)

    # --- _is_concrete_type with abstract class (line 235-236) ---
    def test_isConcreteType__AbstractClass__ReturnsFalseNone(self):
        """Test abstract class returns (False, None) (line 235-236)."""
        store = self._empty_store()

        class AbstractBase(ABC):
            @abstractmethod
            def method(self) -> None:
                pass

        instantiator = self._create_instantiator(store)

        is_concrete, target = instantiator._is_concrete_type(AbstractBase)

        self.assertFalse(is_concrete)
        self.assertIsNone(target)

    # --- _augment_with_inferred_target when class_type is None (line 258-259) ---
    def test_augmentWithInferredTarget__NoClassType__ReturnsNone(self):
        """Test when _extract_class_from_hint returns None (line 258-259)."""
        store = self._empty_store()
        instantiator = self._create_instantiator(store)

        # list[int] is a generic type, _extract_class_from_hint returns None
        result = instantiator._augment_with_inferred_target(
            {"value": 42}, list[int]
        )

        self.assertIsNone(result)

    # --- _could_be_implicit_nested edge cases (line 204-205) ---
    def test_couldBeImplicit__DictWithTarget__ReturnsFalse(self):
        """Test dict with _target_ returns False (line 204-205)."""
        store = self._empty_store()

        @dataclass
        class Model:
            value: int

        instantiator = self._create_instantiator(store)

        result = instantiator._could_be_implicit_nested(
            {"_target_": "model", "value": 42}, Model
        )

        self.assertFalse(result)
