from dataclasses import dataclass
from typing import Optional
from unittest.case import TestCase

from rconfig.ConfigStore import ConfigStore
from rconfig.ConfigValidator import ConfigValidator
from rconfig.ConfigInstantiator import ConfigInstantiator
from rconfig.errors import InstantiationError, MissingFieldError, TargetNotFoundError


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
