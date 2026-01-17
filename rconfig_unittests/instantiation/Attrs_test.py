"""Tests for attrs class instantiation.

These tests verify that rconfig correctly instantiates attrs classes,
including frozen classes, nested structures, and implicit target inference.
"""

from typing import Optional
from unittest import TestCase

import attrs
from attrs import define, frozen, field, Factory

from rconfig.target import TargetRegistry
from rconfig.validation import ConfigValidator
from rconfig.instantiation import ConfigInstantiator


class AttrsInstantiationTests(TestCase):
    """Tests for basic attrs class instantiation."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def _create_instantiator(self, store: TargetRegistry) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__AttrsDefine__ReturnsInstance(self):
        # Arrange
        store = self._empty_store()

        @define
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

        @define
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

    def test_instantiate__NestedAttrsClasses__InstantiatesRecursively(self):
        # Arrange
        store = self._empty_store()

        @define
        class InnerModel:
            value: int

        @define
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

    def test_instantiate__DeeplyNestedAttrs__InstantiatesAllLevels(self):
        # Arrange
        store = self._empty_store()

        @define
        class Level3:
            value: int

        @define
        class Level2:
            level3: Level3

        @define
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

    def test_instantiate__AttrsWithDefaults__UsesDefaultValues(self):
        # Arrange
        store = self._empty_store()

        @define
        class Model:
            required_field: int
            optional_with_default: str = "default_value"
            number_with_default: float = 3.14

        store.register("model", Model)
        instantiator = self._create_instantiator(store)
        config = {"_target_": "model", "required_field": 42}

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertEqual(result.required_field, 42)
        self.assertEqual(result.optional_with_default, "default_value")
        self.assertEqual(result.number_with_default, 3.14)

    def test_instantiate__AttrsWithFactory__UsesFactory(self):
        """Test that attrs Factory defaults are used correctly."""
        # Arrange
        store = self._empty_store()

        @define
        class Model:
            name: str
            items: list = Factory(list)

        store.register("model", Model)
        instantiator = self._create_instantiator(store)
        config = {"_target_": "model", "name": "test"}

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertEqual(result.name, "test")
        self.assertEqual(result.items, [])
        self.assertIsInstance(result.items, list)

    def test_instantiate__AttrsOptionalField__AcceptsNone(self):
        # Arrange
        store = self._empty_store()

        @define
        class Model:
            required: int
            optional: Optional[str] = None

        store.register("model", Model)
        instantiator = self._create_instantiator(store)
        config = {"_target_": "model", "required": 10, "optional": None}

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertEqual(result.required, 10)
        self.assertIsNone(result.optional)


class AttrsFrozenClassTests(TestCase):
    """Tests for frozen attrs class instantiation and immutability."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def _create_instantiator(self, store: TargetRegistry) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__FrozenAttrsClass__ReturnsImmutableInstance(self):
        """Test that frozen attrs classes are instantiated correctly."""
        # Arrange
        store = self._empty_store()

        @frozen
        class FrozenModel:
            hidden_size: int
            dropout: float = 0.1

        store.register("frozen_model", FrozenModel)
        instantiator = self._create_instantiator(store)
        config = {"_target_": "frozen_model", "hidden_size": 256}

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, FrozenModel)
        self.assertEqual(result.hidden_size, 256)
        self.assertEqual(result.dropout, 0.1)

    def test_instantiate__FrozenAttrsClass__ModificationRaisesError(self):
        """Test that attempting to modify a frozen attrs class raises FrozenInstanceError."""
        # Arrange
        store = self._empty_store()

        @frozen
        class FrozenModel:
            value: int

        store.register("frozen_model", FrozenModel)
        instantiator = self._create_instantiator(store)
        config = {"_target_": "frozen_model", "value": 42}
        result = instantiator.instantiate(config)

        # Act & Assert
        with self.assertRaises(attrs.exceptions.FrozenInstanceError):
            result.value = 100

    def test_instantiate__NestedFrozenAttrs__BothAreImmutable(self):
        """Test that nested frozen attrs classes maintain immutability."""
        # Arrange
        store = self._empty_store()

        @frozen
        class InnerFrozen:
            value: int

        @frozen
        class OuterFrozen:
            inner: InnerFrozen
            name: str

        store.register("inner_frozen", InnerFrozen)
        store.register("outer_frozen", OuterFrozen)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "outer_frozen",
            "inner": {"_target_": "inner_frozen", "value": 42},
            "name": "test",
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, OuterFrozen)
        self.assertIsInstance(result.inner, InnerFrozen)
        with self.assertRaises(attrs.exceptions.FrozenInstanceError):
            result.name = "modified"
        with self.assertRaises(attrs.exceptions.FrozenInstanceError):
            result.inner.value = 100


class AttrsImplicitTargetTests(TestCase):
    """Tests for implicit target inference with attrs classes."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def _create_instantiator(self, store: TargetRegistry) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__ImplicitNestedAttrs__InfersTarget(self):
        """Test that nested attrs classes can infer _target_ from type hints."""
        # Arrange
        store = self._empty_store()

        @define
        class InnerModel:
            value: int

        @define
        class OuterModel:
            inner: InnerModel
            name: str

        store.register("inner", InnerModel)
        store.register("outer", OuterModel)
        instantiator = self._create_instantiator(store)

        # Config without explicit _target_ for inner
        config = {
            "_target_": "outer",
            "inner": {"value": 42},  # No _target_ - should be inferred
            "name": "test",
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, OuterModel)
        self.assertIsInstance(result.inner, InnerModel)
        self.assertEqual(result.inner.value, 42)

    def test_instantiate__DeeplyNestedImplicitAttrs__InfersAllTargets(self):
        """Test deeply nested attrs classes with implicit targets."""
        # Arrange
        store = self._empty_store()

        @define
        class Level3:
            value: int

        @define
        class Level2:
            level3: Level3

        @define
        class Level1:
            level2: Level2

        store.register("l3", Level3)
        store.register("l2", Level2)
        store.register("l1", Level1)
        instantiator = self._create_instantiator(store)

        # Config with implicit targets at all nested levels
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

    def test_instantiate__MixedExplicitImplicitAttrs__ReturnsCorrectInstance(self):
        """Test attrs classes with both explicit and implicit targets."""
        # Arrange
        store = self._empty_store()

        @define
        class Config1:
            value: int

        @define
        class Config2:
            value: str

        @define
        class Container:
            config1: Config1
            config2: Config2

        store.register("c1", Config1)
        store.register("c2", Config2)
        store.register("container", Container)
        instantiator = self._create_instantiator(store)

        config = {
            "_target_": "container",
            "config1": {"_target_": "c1", "value": 42},  # Explicit
            "config2": {"value": "hello"},  # Implicit
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, Container)
        self.assertIsInstance(result.config1, Config1)
        self.assertIsInstance(result.config2, Config2)
        self.assertEqual(result.config1.value, 42)
        self.assertEqual(result.config2.value, "hello")


class AttrsListTests(TestCase):
    """Tests for attrs classes with list fields."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def _create_instantiator(self, store: TargetRegistry) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__ListOfAttrsClasses__InstantiatesAll(self):
        """Test instantiation of list containing attrs classes."""
        # Arrange
        store = self._empty_store()

        @define
        class Item:
            value: int

        @define
        class Container:
            items: list[Item]

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
