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
    TargetTypeMismatchError,
    TypeInferenceError,
    TypeMismatchError,
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

    def test_instantiate__NotRegisteredType_ImplicitNested__AutoRegistersAndInstantiates(self):
        """Test unregistered concrete type is auto-registered and instantiated."""
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
            "inner": {"value": 42},
        }

        result = instantiator.instantiate(config)

        # Inner should be auto-registered and instantiated
        self.assertIsInstance(result.inner, Inner)
        self.assertEqual(result.inner.value, 42)
        # Verify Inner was auto-registered
        self.assertIn("inner", store._known_references)

    def test_instantiate__DeeplyNestedUnregistered__AutoRegistersAll(self):
        """Test deeply nested unregistered types are all auto-registered."""
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

        store.register("level1", Level1)  # Only top level registered
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "level1",
            "level2": {
                "level3": {"value": 99}
            },
        }

        result = instantiator.instantiate(config)

        self.assertIsInstance(result.level2, Level2)
        self.assertIsInstance(result.level2.level3, Level3)
        self.assertEqual(result.level2.level3.value, 99)

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

    # === Additional TargetTypeMismatchError Tests ===

    def test_instantiate__ExplicitTarget_SiblingClass__RaisesTargetTypeMismatchError(self):
        """Instantiation with sibling class target fails during validation."""
        # Arrange
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
            item: ChildA

        store.register("child_a", ChildA)
        store.register("child_b", ChildB)
        store.register("container", Container)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "container",
            "item": {"_target_": "child_b", "value": 10},
        }

        # Act & Assert
        with self.assertRaises(TargetTypeMismatchError) as ctx:
            instantiator.instantiate(config)

        self.assertEqual(ctx.exception.field, "item")
        self.assertEqual(ctx.exception.target, "child_b")

    def test_instantiate__ExplicitTarget_WrongTypeNested__RaisesTargetTypeMismatchError(self):
        """Deeply nested wrong type target raises error during instantiation."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class WrongType:
            name: str

        @dataclass
        class CorrectType:
            value: int

        @dataclass
        class Middle:
            inner: CorrectType

        @dataclass
        class Outer:
            middle: Middle

        store.register("wrong_type", WrongType)
        store.register("correct_type", CorrectType)
        store.register("middle", Middle)
        store.register("outer", Outer)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer",
            "middle": {
                "_target_": "middle",
                "inner": {"_target_": "wrong_type", "name": "test"},
            },
        }

        # Act & Assert
        with self.assertRaises(TargetTypeMismatchError) as ctx:
            instantiator.instantiate(config)

        self.assertEqual(ctx.exception.field, "inner")
        self.assertIn("middle.inner", ctx.exception.config_path)

    # === Additional TypeInferenceError Tests ===

    def test_instantiate__ImplicitNested_TypeMismatch__RaisesTypeInferenceError(self):
        """Implicit nested with wrong field type raises TypeInferenceError."""
        # Arrange
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
            "inner": {"value": "not_an_int"},
        }

        # Act & Assert
        with self.assertRaises(TypeInferenceError) as ctx:
            instantiator.instantiate(config)

        self.assertEqual(ctx.exception.field, "inner")
        self.assertEqual(ctx.exception.inferred_type, Inner)
        self.assertEqual(len(ctx.exception.validation_errors), 1)
        self.assertIsInstance(ctx.exception.validation_errors[0], TypeMismatchError)

    def test_instantiate__ImplicitNested_MultipleErrors__RaisesTypeInferenceError(self):
        """Implicit nested with multiple issues raises TypeInferenceError."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Inner:
            required_a: int
            required_b: str

        @dataclass
        class Outer:
            inner: Inner

        store.register("inner", Inner)
        store.register("outer", Outer)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer",
            "inner": {},  # Missing both required fields
        }

        # Act & Assert
        with self.assertRaises(TypeInferenceError) as ctx:
            instantiator.instantiate(config)

        self.assertEqual(len(ctx.exception.validation_errors), 2)
        for wrapped_error in ctx.exception.validation_errors:
            self.assertIsInstance(wrapped_error, MissingFieldError)


class ConfigInstantiatorAutoRegistrationTests(TestCase):
    """Tests for auto-registration during instantiation."""

    def _empty_store(self) -> ConfigStore:
        store = ConfigStore()
        store._known_references.clear()
        return store

    def _create_instantiator(self, store: ConfigStore) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    # === SUCCESS CASES ===

    def test_instantiate__ExplicitTargetMatchesTypeHint__AutoRegistersAndInstantiates(self):
        """Explicit _target_ matching type hint auto-registers and creates instance."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            inner: Inner

        store.register("outer", Outer)
        # Inner is NOT registered
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer",
            "inner": {"_target_": "inner", "value": 42},
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, Outer)
        self.assertIsInstance(result.inner, Inner)
        self.assertEqual(result.inner.value, 42)
        self.assertIn("inner", store._known_references)

    def test_instantiate__NestedExplicitTargets__AutoRegistersAndInstantiatesAll(self):
        """Deeply nested configs with explicit targets all get auto-registered."""
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

        store.register("level1", Level1)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "level1",
            "level2": {
                "_target_": "level2",
                "level3": {"_target_": "level3", "value": 99},
            },
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, Level1)
        self.assertIsInstance(result.level2, Level2)
        self.assertIsInstance(result.level2.level3, Level3)
        self.assertEqual(result.level2.level3.value, 99)
        self.assertIn("level2", store._known_references)
        self.assertIn("level3", store._known_references)

    def test_instantiate__MixedImplicitExplicit__HandlesCorrectly(self):
        """Some nested use implicit inference, others use explicit auto-registration."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class ImplicitType:
            value: int

        @dataclass
        class ExplicitType:
            name: str

        @dataclass
        class Container:
            implicit_field: ImplicitType
            explicit_field: ExplicitType

        # Register ImplicitType for implicit inference, but NOT ExplicitType
        store.register("implicittype", ImplicitType)
        store.register("container", Container)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "container",
            "implicit_field": {"value": 10},  # No _target_ - uses implicit inference
            "explicit_field": {"_target_": "explicittype", "name": "test"},  # Explicit
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result.implicit_field, ImplicitType)
        self.assertIsInstance(result.explicit_field, ExplicitType)
        self.assertEqual(result.implicit_field.value, 10)
        self.assertEqual(result.explicit_field.name, "test")

    def test_instantiate__ExplicitTargetCaseInsensitive__AutoRegisters(self):
        """Target name is matched case-insensitively against class name."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class MyInner:
            value: int

        @dataclass
        class Outer:
            inner: MyInner

        store.register("outer", Outer)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer",
            "inner": {"_target_": "myinner", "value": 42},  # lowercase
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result.inner, MyInner)
        self.assertEqual(result.inner.value, 42)

    # === ERROR CASES ===

    def test_instantiate__ExplicitTargetMismatchesTypeHint__RaisesTargetNotFoundError(self):
        """Explicit _target_ not matching type hint fails with TargetNotFoundError."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            inner: Inner

        store.register("outer", Outer)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer",
            "inner": {"_target_": "wrong_name", "value": 42},
        }

        # Act & Assert
        with self.assertRaises(TargetNotFoundError) as context:
            instantiator.instantiate(config)

        self.assertEqual(context.exception.target, "wrong_name")

    def test_instantiate__ExplicitTargetMissingField__RaisesMissingFieldError(self):
        """Auto-registered target with missing required field fails."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Inner:
            required_value: int

        @dataclass
        class Outer:
            inner: Inner

        store.register("outer", Outer)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer",
            "inner": {"_target_": "inner"},  # Missing required_value
        }

        # Act & Assert
        with self.assertRaises(MissingFieldError) as context:
            instantiator.instantiate(config)

        self.assertEqual(context.exception.field, "required_value")

    def test_instantiate__ExplicitTargetConstructorFails__RaisesInstantiationError(self):
        """Auto-registered target that fails during construction."""
        # Arrange
        store = self._empty_store()

        class FailingClass:
            def __init__(self, value: int) -> None:
                raise ValueError("Construction failed!")

        @dataclass
        class Container:
            item: FailingClass

        store.register("container", Container)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "container",
            "item": {"_target_": "failingclass", "value": 10},
        }

        # Act & Assert
        with self.assertRaises(InstantiationError) as context:
            instantiator.instantiate(config)

        self.assertEqual(context.exception.target, "failingclass")
        self.assertIn("Construction failed!", context.exception.reason)

    def test_instantiate__ExplicitTargetWithOptionalType__AutoRegisters(self):
        """Optional[SomeClass] type hint with matching _target_ auto-registers."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            inner: Optional[Inner]

        store.register("outer", Outer)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer",
            "inner": {"_target_": "inner", "value": 42},
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result.inner, Inner)
        self.assertEqual(result.inner.value, 42)
        self.assertIn("inner", store._known_references)


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


class ConfigInstantiatorSharedInstanceTests(TestCase):
    """Tests for shared instance instantiation via instance_targets."""

    def _empty_store(self) -> ConfigStore:
        store = ConfigStore()
        store._known_references.clear()
        return store

    def _create_instantiator(self, store: ConfigStore) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__TwoFieldsSameTarget__ShareSameObject(self):
        """Test that two _instance_ references to the same target share the object."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Database:
            url: str

        @dataclass
        class ServiceA:
            db: Database

        @dataclass
        class ServiceB:
            db: Database

        @dataclass
        class App:
            shared_db: Database
            service_a: ServiceA
            service_b: ServiceB

        store.register("database", Database)
        store.register("service_a", ServiceA)
        store.register("service_b", ServiceB)
        store.register("app", App)
        instantiator = self._create_instantiator(store)

        # Simulate composed config where _instance_ has been resolved
        # by copying the referenced value
        config = {
            "_target_": "app",
            "shared_db": {
                "_target_": "database",
                "url": "postgres://localhost",
            },
            "service_a": {
                "_target_": "service_a",
                "db": {
                    "_target_": "database",
                    "url": "postgres://localhost",
                },
            },
            "service_b": {
                "_target_": "service_b",
                "db": {
                    "_target_": "database",
                    "url": "postgres://localhost",
                },
            },
        }

        # Instance targets indicate that service_a.db and service_b.db
        # both reference shared_db
        instance_targets = {
            "service_a.db": "shared_db",
            "service_b.db": "shared_db",
        }

        # Act
        result = instantiator.instantiate(
            config, validate=True, instance_targets=instance_targets
        )

        # Assert
        self.assertIsInstance(result, App)
        self.assertIsInstance(result.shared_db, Database)
        self.assertIsInstance(result.service_a, ServiceA)
        self.assertIsInstance(result.service_b, ServiceB)

        # The key assertion: all three db fields point to the SAME object
        self.assertIs(result.service_a.db, result.shared_db)
        self.assertIs(result.service_b.db, result.shared_db)
        self.assertIs(result.service_a.db, result.service_b.db)

    def test_instantiate__InstanceToNull__ReturnsNone(self):
        """Test that _instance_: null returns None."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Service:
            db: Optional["Database"]  # noqa: F821

        @dataclass
        class Database:
            url: str

        store.register("database", Database)
        store.register("service", Service)
        instantiator = self._create_instantiator(store)

        config = {
            "_target_": "service",
            "db": None,  # Already resolved to None by composer
        }

        instance_targets = {
            "db": None,  # _instance_: null
        }

        # Act
        result = instantiator.instantiate(
            config, validate=False, instance_targets=instance_targets
        )

        # Assert
        self.assertIsNone(result.db)

    def test_instantiate__NoInstanceTargets__WorksNormally(self):
        """Test that without instance_targets, instantiation works as before."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            a: Inner
            b: Inner

        store.register("inner", Inner)
        store.register("outer", Outer)
        instantiator = self._create_instantiator(store)

        config = {
            "_target_": "outer",
            "a": {"_target_": "inner", "value": 1},
            "b": {"_target_": "inner", "value": 2},
        }

        # Act - no instance_targets
        result = instantiator.instantiate(config)

        # Assert - different objects even with same structure
        self.assertIsInstance(result.a, Inner)
        self.assertIsInstance(result.b, Inner)
        self.assertIsNot(result.a, result.b)  # Different objects
        self.assertEqual(result.a.value, 1)
        self.assertEqual(result.b.value, 2)

    def test_instantiate__ChainedInstances__AllShareSameObject(self):
        """Test that chained instances (A->B->C) all share the same object."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Database:
            url: str

        @dataclass
        class Container:
            original: Database
            alias: Database
            final: Database

        store.register("database", Database)
        store.register("container", Container)
        instantiator = self._create_instantiator(store)

        # Config after composition (all fields have same config)
        config = {
            "_target_": "container",
            "original": {"_target_": "database", "url": "postgres://localhost"},
            "alias": {"_target_": "database", "url": "postgres://localhost"},
            "final": {"_target_": "database", "url": "postgres://localhost"},
        }

        # alias -> original, final -> original (chain resolved)
        instance_targets = {
            "alias": "original",
            "final": "original",
        }

        # Act
        result = instantiator.instantiate(
            config, validate=True, instance_targets=instance_targets
        )

        # Assert
        self.assertIs(result.alias, result.original)
        self.assertIs(result.final, result.original)

    def test_instantiate__NestedInstanceSharing__WorksCorrectly(self):
        """Test instance sharing works in deeply nested structures."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Cache:
            size: int

        @dataclass
        class ServiceA:
            cache: Cache

        @dataclass
        class ServiceB:
            cache: Cache

        @dataclass
        class ServiceContainer:
            service_a: ServiceA
            service_b: ServiceB

        @dataclass
        class App:
            shared_cache: Cache
            services: ServiceContainer

        store.register("cache", Cache)
        store.register("service_a", ServiceA)
        store.register("service_b", ServiceB)
        store.register("service_container", ServiceContainer)
        store.register("app", App)
        instantiator = self._create_instantiator(store)

        config = {
            "_target_": "app",
            "shared_cache": {"_target_": "cache", "size": 100},
            "services": {
                "_target_": "service_container",
                "service_a": {
                    "_target_": "service_a",
                    "cache": {"_target_": "cache", "size": 100},
                },
                "service_b": {
                    "_target_": "service_b",
                    "cache": {"_target_": "cache", "size": 100},
                },
            },
        }

        instance_targets = {
            "services.service_a.cache": "shared_cache",
            "services.service_b.cache": "shared_cache",
        }

        # Act
        result = instantiator.instantiate(
            config, validate=True, instance_targets=instance_targets
        )

        # Assert
        self.assertIs(result.services.service_a.cache, result.shared_cache)
        self.assertIs(result.services.service_b.cache, result.shared_cache)

    def test_instantiate__InstanceInList__SharesCorrectly(self):
        """Test instance sharing works with list indexing."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Database:
            name: str

        @dataclass
        class App:
            primary_db: Database
            replicas: list

        store.register("database", Database)
        store.register("app", App)
        instantiator = self._create_instantiator(store)

        config = {
            "_target_": "app",
            "primary_db": {"_target_": "database", "name": "primary"},
            "replicas": [
                {"_target_": "database", "name": "primary"},  # _instance_: primary_db
                {"_target_": "database", "name": "replica"},  # Not an instance
            ],
        }

        instance_targets = {
            "replicas[0]": "primary_db",
        }

        # Act
        result = instantiator.instantiate(
            config, validate=True, instance_targets=instance_targets
        )

        # Assert
        self.assertIs(result.replicas[0], result.primary_db)
        self.assertIsNot(result.replicas[1], result.primary_db)

    def test_instantiate__TargetInstantiatedBeforeInstance__SharesCorrectly(self):
        """Test that when target is instantiated first, instances share it."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Database:
            url: str

        @dataclass
        class App:
            db: Database  # Instantiated first
            db_alias: Database  # Instance of db

        store.register("database", Database)
        store.register("app", App)
        instantiator = self._create_instantiator(store)

        config = {
            "_target_": "app",
            "db": {"_target_": "database", "url": "postgres://localhost"},
            "db_alias": {"_target_": "database", "url": "postgres://localhost"},
        }

        instance_targets = {
            "db_alias": "db",
        }

        # Act
        result = instantiator.instantiate(
            config, validate=True, instance_targets=instance_targets
        )

        # Assert
        self.assertIs(result.db_alias, result.db)

    def test_instantiate__InstanceReferencesNestedTarget__SharesCorrectly(self):
        """Test instance references to a nested path work correctly."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Database:
            url: str

        @dataclass
        class Services:
            db: Database

        @dataclass
        class App:
            services: Services
            shared_db: Database  # Instance of services.db

        store.register("database", Database)
        store.register("services", Services)
        store.register("app", App)
        instantiator = self._create_instantiator(store)

        config = {
            "_target_": "app",
            "services": {
                "_target_": "services",
                "db": {"_target_": "database", "url": "postgres://localhost"},
            },
            "shared_db": {"_target_": "database", "url": "postgres://localhost"},
        }

        # shared_db references services.db
        instance_targets = {
            "shared_db": "services.db",
        }

        # Act
        result = instantiator.instantiate(
            config, validate=True, instance_targets=instance_targets
        )

        # Assert
        self.assertIs(result.shared_db, result.services.db)

    def test_instantiate__NestedInstantiationError__RaisesWithPath(self):
        """Test that instantiation errors in nested configs include the path."""
        # Arrange
        store = self._empty_store()

        class FailingClass:
            def __init__(self, value: int):
                raise ValueError("Intentional failure")

        @dataclass
        class Container:
            failing: "FailingClass"

        store.register("failing", FailingClass)
        store.register("container", Container)
        instantiator = self._create_instantiator(store)

        config = {
            "_target_": "container",
            "failing": {"_target_": "failing", "value": 42},
        }

        # _instantiate_nested is used for nested configs
        # Act & Assert
        with self.assertRaises(InstantiationError) as context:
            instantiator.instantiate(config)

        self.assertEqual(context.exception.target, "failing")
        self.assertEqual(context.exception.config_path, "failing")

    def test_instantiate__TopLevelWithConfigPath__CachesCorrectly(self):
        """Test that top-level instantiate with config_path caches correctly."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            value: int

        store.register("model", Model)
        instantiator = self._create_instantiator(store)

        config = {"_target_": "model", "value": 42}

        # Act - Call with a config_path
        result = instantiator.instantiate(
            config, validate=True, config_path="root_model"
        )

        # Assert
        self.assertIsInstance(result, Model)
        self.assertEqual(result.value, 42)
        # Check that it was cached
        self.assertEqual(instantiator._instantiated_cache.get("root_model"), result)


class ConfigInstantiatorCoverageTests(TestCase):
    """Tests to improve ConfigInstantiator coverage for edge cases."""

    def _empty_store(self) -> ConfigStore:
        store = ConfigStore()
        store._known_references.clear()
        return store

    def _create_instantiator(self, store: ConfigStore) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__UnregisteredTargetMatchingTypeHint__AutoRegisters(self):
        """Test auto-registration when target name matches type hint class name."""
        # Arrange - lines 146-152
        store = self._empty_store()

        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            inner: Inner  # Type hint is Inner

        # Only register outer, not inner
        store.register("outer", Outer)
        instantiator = self._create_instantiator(store)

        # Config uses "inner" as target name which matches Inner class name
        config = {
            "_target_": "outer",
            "inner": {"_target_": "inner", "value": 42},
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert - should have auto-registered and instantiated
        self.assertIsInstance(result, Outer)
        self.assertIsInstance(result.inner, Inner)
        self.assertEqual(result.inner.value, 42)

    def test_instantiate_nested__CacheHit__ReturnsSharedInstance(self):
        """Test that cache hits return the same instance during nested instantiation."""
        # Arrange - lines 190-192, 196, 201
        store = self._empty_store()

        @dataclass
        class Database:
            url: str

        @dataclass
        class App:
            db1: Database
            db2: Database

        store.register("database", Database)
        store.register("app", App)
        instantiator = self._create_instantiator(store)

        config = {
            "_target_": "app",
            "db1": {"_target_": "database", "url": "postgres://localhost"},
            "db2": {"_target_": "database", "url": "postgres://localhost"},
        }

        # Instance targets make db2 share db1's instance
        instance_targets = {
            "db2": "db1",
        }

        # Act
        result = instantiator.instantiate(config, instance_targets=instance_targets)

        # Assert - both should be the same object
        self.assertIs(result.db1, result.db2)

    def test_find_exact_match__NoMatch__ReturnsNone(self):
        """Test _find_exact_match returns None when no exact match found."""
        # Arrange - line 302
        store = self._empty_store()

        @dataclass
        class UnregisteredClass:
            value: int

        instantiator = self._create_instantiator(store)

        # Act
        result = instantiator._find_exact_match(UnregisteredClass)

        # Assert
        self.assertIsNone(result)

    def test_is_concrete_type__NameCollision__UsesFullyQualifiedName(self):
        """Test auto-registration with name collision uses fully qualified name."""
        # Arrange - lines 329-340
        store = self._empty_store()

        @dataclass
        class MyClass:
            value: int

        # Pre-register a class with the same lowercase name
        @dataclass
        class AnotherMyClass:
            other: str

        store.register("myclass", AnotherMyClass)
        instantiator = self._create_instantiator(store)

        # Act - this should trigger name collision handling
        is_concrete, inferred_target = instantiator._is_concrete_type(MyClass)

        # Assert - should use fully qualified name due to collision
        self.assertTrue(is_concrete)
        self.assertIsNotNone(inferred_target)
        # The name should be the fully qualified name since "myclass" is taken
        self.assertIn(".", inferred_target)  # Contains module.ClassName

    def test_augment_with_inferred_target__NonConcreteType__ReturnsNone(self):
        """Test _augment_with_inferred_target returns None for non-concrete types."""
        # Arrange - line 361
        store = self._empty_store()

        class AbstractBase(ABC):
            @abstractmethod
            def method(self): ...

        instantiator = self._create_instantiator(store)
        value = {"some_field": "value"}

        # Act - AbstractBase is not concrete
        result = instantiator._augment_with_inferred_target(value, AbstractBase)

        # Assert
        self.assertIsNone(result)

    def test_augment_with_inferred_target__AmbiguousType__ReturnsNone(self):
        """Test _augment_with_inferred_target returns None for ambiguous types."""
        # Arrange - line 361
        store = self._empty_store()

        class BaseClass:
            pass

        class SubClass1(BaseClass):
            pass

        class SubClass2(BaseClass):
            pass

        # Register multiple subclasses - makes BaseClass ambiguous
        store.register("sub1", SubClass1)
        store.register("sub2", SubClass2)
        instantiator = self._create_instantiator(store)
        value = {"some_field": "value"}

        # Act - BaseClass is ambiguous (multiple registered subclasses)
        result = instantiator._augment_with_inferred_target(value, BaseClass)

        # Assert
        self.assertIsNone(result)
