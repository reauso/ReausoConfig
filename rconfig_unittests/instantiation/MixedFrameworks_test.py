"""Tests for mixed framework interoperability.

These tests verify that rconfig correctly handles configurations where
different framework types (dataclasses, Pydantic, attrs) are nested
within each other.
"""

from dataclasses import dataclass
from unittest import TestCase

from pydantic import BaseModel, ConfigDict
from attrs import define

from rconfig.target import TargetRegistry
from rconfig.validation import ConfigValidator
from rconfig.instantiation import ConfigInstantiator


class MixedFrameworkTests(TestCase):
    """Tests for interoperability between dataclasses, Pydantic, and attrs."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def _create_instantiator(self, store: TargetRegistry) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__DataclassContainingPydantic__Works(self):
        """Test dataclass with Pydantic model as nested field."""
        # Arrange
        store = self._empty_store()

        class PydanticInner(BaseModel):
            value: int

        @dataclass
        class DataclassOuter:
            inner: PydanticInner
            name: str

        store.register("pydantic_inner", PydanticInner)
        store.register("dataclass_outer", DataclassOuter)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "dataclass_outer",
            "inner": {"_target_": "pydantic_inner", "value": 42},
            "name": "test",
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, DataclassOuter)
        self.assertIsInstance(result.inner, PydanticInner)
        self.assertEqual(result.inner.value, 42)
        self.assertEqual(result.name, "test")

    def test_instantiate__PydanticContainingDataclass__Works(self):
        """Test Pydantic model with dataclass as nested field."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class DataclassInner:
            value: int

        class PydanticOuter(BaseModel):
            inner: DataclassInner
            name: str

        store.register("dataclass_inner", DataclassInner)
        store.register("pydantic_outer", PydanticOuter)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "pydantic_outer",
            "inner": {"_target_": "dataclass_inner", "value": 42},
            "name": "test",
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, PydanticOuter)
        self.assertIsInstance(result.inner, DataclassInner)
        self.assertEqual(result.inner.value, 42)
        self.assertEqual(result.name, "test")

    def test_instantiate__DataclassContainingAttrs__Works(self):
        """Test dataclass with attrs class as nested field."""
        # Arrange
        store = self._empty_store()

        @define
        class AttrsInner:
            value: int

        @dataclass
        class DataclassOuter:
            inner: AttrsInner
            name: str

        store.register("attrs_inner", AttrsInner)
        store.register("dataclass_outer", DataclassOuter)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "dataclass_outer",
            "inner": {"_target_": "attrs_inner", "value": 42},
            "name": "test",
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, DataclassOuter)
        self.assertIsInstance(result.inner, AttrsInner)
        self.assertEqual(result.inner.value, 42)
        self.assertEqual(result.name, "test")

    def test_instantiate__AttrsContainingDataclass__Works(self):
        """Test attrs class with dataclass as nested field."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class DataclassInner:
            value: int

        @define
        class AttrsOuter:
            inner: DataclassInner
            name: str

        store.register("dataclass_inner", DataclassInner)
        store.register("attrs_outer", AttrsOuter)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "attrs_outer",
            "inner": {"_target_": "dataclass_inner", "value": 42},
            "name": "test",
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, AttrsOuter)
        self.assertIsInstance(result.inner, DataclassInner)
        self.assertEqual(result.inner.value, 42)
        self.assertEqual(result.name, "test")

    def test_instantiate__PydanticContainingAttrs__Works(self):
        """Test Pydantic model with attrs class as nested field."""
        # Arrange
        store = self._empty_store()

        @define
        class AttrsInner:
            value: int

        class PydanticOuter(BaseModel):
            model_config = ConfigDict(arbitrary_types_allowed=True)

            inner: AttrsInner
            name: str

        store.register("attrs_inner", AttrsInner)
        store.register("pydantic_outer", PydanticOuter)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "pydantic_outer",
            "inner": {"_target_": "attrs_inner", "value": 42},
            "name": "test",
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, PydanticOuter)
        self.assertIsInstance(result.inner, AttrsInner)
        self.assertEqual(result.inner.value, 42)
        self.assertEqual(result.name, "test")

    def test_instantiate__AttrsContainingPydantic__Works(self):
        """Test attrs class with Pydantic model as nested field."""
        # Arrange
        store = self._empty_store()

        class PydanticInner(BaseModel):
            value: int

        @define
        class AttrsOuter:
            inner: PydanticInner
            name: str

        store.register("pydantic_inner", PydanticInner)
        store.register("attrs_outer", AttrsOuter)
        instantiator = self._create_instantiator(store)
        config = {
            "_target_": "attrs_outer",
            "inner": {"_target_": "pydantic_inner", "value": 42},
            "name": "test",
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, AttrsOuter)
        self.assertIsInstance(result.inner, PydanticInner)
        self.assertEqual(result.inner.value, 42)
        self.assertEqual(result.name, "test")


class MixedFrameworkImplicitTargetTests(TestCase):
    """Tests for implicit target inference across mixed frameworks."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def _create_instantiator(self, store: TargetRegistry) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__DataclassWithImplicitPydantic__InfersTarget(self):
        """Test dataclass with implicit Pydantic nested target."""
        # Arrange
        store = self._empty_store()

        class PydanticInner(BaseModel):
            value: int

        @dataclass
        class DataclassOuter:
            inner: PydanticInner
            name: str

        store.register("pydantic_inner", PydanticInner)
        store.register("dataclass_outer", DataclassOuter)
        instantiator = self._create_instantiator(store)

        # Config without explicit _target_ for inner
        config = {
            "_target_": "dataclass_outer",
            "inner": {"value": 42},  # No _target_ - should be inferred
            "name": "test",
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, DataclassOuter)
        self.assertIsInstance(result.inner, PydanticInner)
        self.assertEqual(result.inner.value, 42)

    def test_instantiate__PydanticWithImplicitDataclass__InfersTarget(self):
        """Test Pydantic model with implicit dataclass nested target."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class DataclassInner:
            value: int

        class PydanticOuter(BaseModel):
            inner: DataclassInner
            name: str

        store.register("dataclass_inner", DataclassInner)
        store.register("pydantic_outer", PydanticOuter)
        instantiator = self._create_instantiator(store)

        # Config without explicit _target_ for inner
        config = {
            "_target_": "pydantic_outer",
            "inner": {"value": 42},  # No _target_ - should be inferred
            "name": "test",
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, PydanticOuter)
        self.assertIsInstance(result.inner, DataclassInner)
        self.assertEqual(result.inner.value, 42)

    def test_instantiate__AttrsWithImplicitDataclass__InfersTarget(self):
        """Test attrs class with implicit dataclass nested target."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class DataclassInner:
            value: int

        @define
        class AttrsOuter:
            inner: DataclassInner
            name: str

        store.register("dataclass_inner", DataclassInner)
        store.register("attrs_outer", AttrsOuter)
        instantiator = self._create_instantiator(store)

        # Config without explicit _target_ for inner
        config = {
            "_target_": "attrs_outer",
            "inner": {"value": 42},  # No _target_ - should be inferred
            "name": "test",
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, AttrsOuter)
        self.assertIsInstance(result.inner, DataclassInner)
        self.assertEqual(result.inner.value, 42)


class TripleMixedFrameworkTests(TestCase):
    """Tests for configurations using all three frameworks together."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def _create_instantiator(self, store: TargetRegistry) -> ConfigInstantiator:
        validator = ConfigValidator(store)
        return ConfigInstantiator(store, validator)

    def test_instantiate__AllThreeFrameworks__Works(self):
        """Test configuration using dataclass, Pydantic, and attrs together."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class DataclassConfig:
            value: int

        class PydanticConfig(BaseModel):
            value: str

        @define
        class AttrsConfig:
            value: float

        @dataclass
        class Container:
            dc: DataclassConfig
            pydantic: PydanticConfig
            attrs: AttrsConfig

        store.register("dc", DataclassConfig)
        store.register("pyd", PydanticConfig)
        store.register("att", AttrsConfig)
        store.register("container", Container)
        instantiator = self._create_instantiator(store)

        config = {
            "_target_": "container",
            "dc": {"_target_": "dc", "value": 42},
            "pydantic": {"_target_": "pyd", "value": "hello"},
            "attrs": {"_target_": "att", "value": 3.14},
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, Container)
        self.assertIsInstance(result.dc, DataclassConfig)
        self.assertIsInstance(result.pydantic, PydanticConfig)
        self.assertIsInstance(result.attrs, AttrsConfig)
        self.assertEqual(result.dc.value, 42)
        self.assertEqual(result.pydantic.value, "hello")
        self.assertEqual(result.attrs.value, 3.14)

    def test_instantiate__AllThreeFrameworksImplicit__InfersAllTargets(self):
        """Test all three frameworks with implicit target inference."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class DataclassConfig:
            value: int

        class PydanticConfig(BaseModel):
            value: str

        @define
        class AttrsConfig:
            value: float

        @dataclass
        class Container:
            dc: DataclassConfig
            pydantic: PydanticConfig
            attrs: AttrsConfig

        store.register("dc", DataclassConfig)
        store.register("pyd", PydanticConfig)
        store.register("att", AttrsConfig)
        store.register("container", Container)
        instantiator = self._create_instantiator(store)

        # All nested configs without explicit _target_
        config = {
            "_target_": "container",
            "dc": {"value": 42},
            "pydantic": {"value": "hello"},
            "attrs": {"value": 3.14},
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, Container)
        self.assertIsInstance(result.dc, DataclassConfig)
        self.assertIsInstance(result.pydantic, PydanticConfig)
        self.assertIsInstance(result.attrs, AttrsConfig)
        self.assertEqual(result.dc.value, 42)
        self.assertEqual(result.pydantic.value, "hello")
        self.assertEqual(result.attrs.value, 3.14)
