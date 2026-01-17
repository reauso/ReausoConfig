"""Tests for Pydantic model instantiation.

These tests verify that rconfig correctly instantiates Pydantic BaseModel classes,
including frozen models, nested structures, and implicit target inference.
"""

from typing import Optional
from unittest import TestCase

from pydantic import BaseModel, ConfigDict, ValidationError

from rconfig.target import TargetRegistry
from rconfig.validation import ConfigValidator
from rconfig.instantiation import ConfigInstantiator


class PydanticInstantiationTests(TestCase):
    """Tests for basic Pydantic BaseModel instantiation."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def _create_instantiator(self, store: TargetRegistry) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__PydanticBaseModel__ReturnsInstance(self):
        # Arrange
        store = self._empty_store()

        class Model(BaseModel):
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

        class Model(BaseModel):
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

    def test_instantiate__NestedPydanticModels__InstantiatesRecursively(self):
        # Arrange
        store = self._empty_store()

        class InnerModel(BaseModel):
            value: int

        class OuterModel(BaseModel):
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

    def test_instantiate__DeeplyNestedPydantic__InstantiatesAllLevels(self):
        # Arrange
        store = self._empty_store()

        class Level3(BaseModel):
            value: int

        class Level2(BaseModel):
            level3: Level3

        class Level1(BaseModel):
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

    def test_instantiate__PydanticWithDefaults__UsesDefaultValues(self):
        # Arrange
        store = self._empty_store()

        class Model(BaseModel):
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

    def test_instantiate__PydanticOptionalField__AcceptsNone(self):
        # Arrange
        store = self._empty_store()

        class Model(BaseModel):
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


class PydanticFrozenModelTests(TestCase):
    """Tests for frozen Pydantic model instantiation and immutability."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def _create_instantiator(self, store: TargetRegistry) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__FrozenPydanticModel__ReturnsImmutableInstance(self):
        """Test that frozen Pydantic models are instantiated correctly."""
        # Arrange
        store = self._empty_store()

        class FrozenModel(BaseModel):
            model_config = ConfigDict(frozen=True)

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

    def test_instantiate__FrozenPydanticModel__ModificationRaisesValidationError(self):
        """Test that attempting to modify a frozen Pydantic model raises ValidationError."""
        # Arrange
        store = self._empty_store()

        class FrozenModel(BaseModel):
            model_config = ConfigDict(frozen=True)

            value: int

        store.register("frozen_model", FrozenModel)
        instantiator = self._create_instantiator(store)
        config = {"_target_": "frozen_model", "value": 42}
        result = instantiator.instantiate(config)

        # Act & Assert
        with self.assertRaises(ValidationError):
            result.value = 100

    def test_instantiate__NestedFrozenPydantic__BothAreImmutable(self):
        """Test that nested frozen Pydantic models maintain immutability."""
        # Arrange
        store = self._empty_store()

        class InnerFrozen(BaseModel):
            model_config = ConfigDict(frozen=True)

            value: int

        class OuterFrozen(BaseModel):
            model_config = ConfigDict(frozen=True)

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
        with self.assertRaises(ValidationError):
            result.name = "modified"
        with self.assertRaises(ValidationError):
            result.inner.value = 100


class PydanticImplicitTargetTests(TestCase):
    """Tests for implicit target inference with Pydantic models."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def _create_instantiator(self, store: TargetRegistry) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__ImplicitNestedPydantic__InfersTarget(self):
        """Test that nested Pydantic models can infer _target_ from type hints."""
        # Arrange
        store = self._empty_store()

        class InnerModel(BaseModel):
            value: int

        class OuterModel(BaseModel):
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

    def test_instantiate__DeeplyNestedImplicitPydantic__InfersAllTargets(self):
        """Test deeply nested Pydantic models with implicit targets."""
        # Arrange
        store = self._empty_store()

        class Level3(BaseModel):
            value: int

        class Level2(BaseModel):
            level3: Level3

        class Level1(BaseModel):
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

    def test_instantiate__MixedExplicitImplicitPydantic__ReturnsCorrectInstance(self):
        """Test Pydantic models with both explicit and implicit targets."""
        # Arrange
        store = self._empty_store()

        class Config1(BaseModel):
            value: int

        class Config2(BaseModel):
            value: str

        class Container(BaseModel):
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


class PydanticListTests(TestCase):
    """Tests for Pydantic models with list fields."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def _create_instantiator(self, store: TargetRegistry) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__ListOfPydanticModels__InstantiatesAll(self):
        """Test instantiation of list containing Pydantic models."""
        # Arrange
        store = self._empty_store()

        class Item(BaseModel):
            value: int

        class Container(BaseModel):
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
