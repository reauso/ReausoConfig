"""Tests for type inference from parent's type hints."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Annotated, Optional, Union
from unittest import TestCase

from rconfig._internal.type_inference import infer_target_from_parent
from rconfig.target import TargetRegistry


class InferTargetFromParentTests(TestCase):
    """Tests for infer_target_from_parent function."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def test_inferTargetFromParent__ConcreteTypeHint__ReturnsTarget(self):
        """Type inference works when parent has concrete type hint."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Database:
            port: int

        @dataclass
        class Model:
            database: Database

        store.register("model", Model)
        store.register("database", Database)

        config = {
            "model": {
                "_target_": "model",
                "database": {"port": 5432},
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.database", store)

        # Assert
        self.assertEqual(result, "database")

    def test_inferTargetFromParent__OptionalTypeHint__ReturnsTarget(self):
        """Type inference works with Optional[X] type hints."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Database:
            port: int

        @dataclass
        class Model:
            database: Optional[Database]

        store.register("model", Model)
        store.register("database", Database)

        config = {
            "model": {
                "_target_": "model",
                "database": {"port": 5432},
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.database", store)

        # Assert
        self.assertEqual(result, "database")

    def test_inferTargetFromParent__RootPath__ReturnsNone(self):
        """Cannot infer type for root level (no parent)."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            size: int

        store.register("model", Model)
        config = {"size": 256}

        # Act
        result = infer_target_from_parent(config, "size", store)

        # Assert - 'size' is a single segment, no parent to infer from
        self.assertIsNone(result)

    def test_inferTargetFromParent__ParentNoTarget__ReturnsNone(self):
        """Cannot infer if parent has no _target_."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Database:
            port: int

        store.register("database", Database)

        config = {
            "model": {
                # No _target_!
                "database": {"port": 5432},
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.database", store)

        # Assert
        self.assertIsNone(result)

    def test_inferTargetFromParent__AbstractType__ReturnsNone(self):
        """Cannot infer abstract types."""
        # Arrange
        store = self._empty_store()

        class AbstractDatabase(ABC):
            @abstractmethod
            def connect(self) -> None:
                pass

        @dataclass
        class Model:
            database: AbstractDatabase

        store.register("model", Model)

        config = {
            "model": {
                "_target_": "model",
                "database": {"port": 5432},
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.database", store)

        # Assert - abstract type cannot be inferred
        self.assertIsNone(result)

    def test_inferTargetFromParent__UnionTypeStructuralMatch__InfersCorrectType(self):
        """Union types are resolved via structural matching."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class DatabaseA:
            port: int

        @dataclass
        class DatabaseB:
            host: str

        @dataclass
        class Model:
            database: Union[DatabaseA, DatabaseB]

        store.register("model", Model)
        store.register("database_a", DatabaseA)
        store.register("database_b", DatabaseB)

        config = {
            "model": {
                "_target_": "model",
                "database": {"port": 5432},
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.database", store)

        # Assert - structural match identifies DatabaseA (has required port: int)
        self.assertEqual(result, "database_a")

    def test_inferTargetFromParent__UnknownParentTarget__ReturnsNone(self):
        """Returns None if parent's _target_ is not registered."""
        # Arrange
        store = self._empty_store()

        config = {
            "model": {
                "_target_": "unknown_target",
                "database": {"port": 5432},
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.database", store)

        # Assert
        self.assertIsNone(result)

    def test_inferTargetFromParent__NoTypeHintForField__ReturnsNone(self):
        """Returns None if field has no type hint."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            size: int
            # No type hint for 'database'

        store.register("model", Model)

        config = {
            "model": {
                "_target_": "model",
                "database": {"port": 5432},
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.database", store)

        # Assert
        self.assertIsNone(result)

    def test_inferTargetFromParent__DeeplyNested__Works(self):
        """Type inference works for deeply nested paths."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Cache:
            size: int

        @dataclass
        class Database:
            cache: Cache

        @dataclass
        class Model:
            database: Database

        store.register("model", Model)
        store.register("database", Database)
        store.register("cache", Cache)

        config = {
            "model": {
                "_target_": "model",
                "database": {
                    "_target_": "database",
                    "cache": {"size": 100},
                },
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.database.cache", store)

        # Assert
        self.assertEqual(result, "cache")

    def test_inferTargetFromParent__ListIndex__InfersElementType(self):
        """Infer type for list indices from list[X] type hint."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Callback:
            name: str

        @dataclass
        class Model:
            callbacks: list[Callback]

        store.register("model", Model)
        store.register("callback", Callback)

        config = {
            "model": {
                "_target_": "model",
                "callbacks": [{"name": "first"}],
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.callbacks[0]", store)

        # Assert - list element type inferred from list[Callback]
        self.assertEqual(result, "callback")

    def test_inferTargetFromParent__PrimitiveType__ReturnsNone(self):
        """Returns None for primitive types (int, str, etc.)."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            size: int

        store.register("model", Model)

        config = {
            "model": {
                "_target_": "model",
                "size": 256,
            }
        }

        # Act - 'size' is an int, not instantiable
        result = infer_target_from_parent(config, "model.size", store)

        # Assert - primitive types cannot be inferred
        self.assertIsNone(result)

    def test_inferTargetFromParent__InvalidPath__ReturnsNone(self):
        """Returns None for paths that don't exist in config."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            size: int

        store.register("model", Model)
        config = {"model": {"_target_": "model", "size": 256}}

        # Act
        result = infer_target_from_parent(config, "model.nonexistent", store)

        # Assert
        self.assertIsNone(result)

    def test_inferTargetFromParent__AutoRegisters__WhenNoTargetExists(self):
        """Type inference auto-registers the class if no target exists."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Database:
            port: int

        @dataclass
        class Model:
            database: Database

        store.register("model", Model)
        # Note: Database is NOT registered

        config = {
            "model": {
                "_target_": "model",
                "database": {"port": 5432},
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.database", store)

        # Assert - should auto-register and return the target name
        self.assertIsNotNone(result)
        self.assertIn("database", result.lower())


class ListElementTypeInferenceTests(TestCase):
    """Tests for list element type inference."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def test_inferListElement__ParameterizedList__Works(self):
        """Infer element type from list[X] type hint."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Callback:
            name: str

        @dataclass
        class Trainer:
            callbacks: list[Callback]

        store.register("trainer", Trainer)
        store.register("callback", Callback)

        config = {
            "trainer": {
                "_target_": "trainer",
                "callbacks": [{"name": "first"}, {"name": "second"}],
            }
        }

        # Act
        result = infer_target_from_parent(config, "trainer.callbacks[0]", store)

        # Assert
        self.assertEqual(result, "callback")

    def test_inferListElement__SecondElement__Works(self):
        """Infer type works for any list index, not just [0]."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Callback:
            name: str

        @dataclass
        class Trainer:
            callbacks: list[Callback]

        store.register("trainer", Trainer)
        store.register("callback", Callback)

        config = {
            "trainer": {
                "_target_": "trainer",
                "callbacks": [{"name": "first"}, {"name": "second"}],
            }
        }

        # Act
        result = infer_target_from_parent(config, "trainer.callbacks[1]", store)

        # Assert
        self.assertEqual(result, "callback")

    def test_inferListElement__UnparameterizedList__ReturnsNone(self):
        """Cannot infer from unparameterized list (just 'list')."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Trainer:
            callbacks: list  # No type parameter

        store.register("trainer", Trainer)

        config = {
            "trainer": {
                "_target_": "trainer",
                "callbacks": [{"name": "first"}],
            }
        }

        # Act
        result = infer_target_from_parent(config, "trainer.callbacks[0]", store)

        # Assert
        self.assertIsNone(result)

    def test_inferListElement__GrandparentNoTarget__ReturnsNone(self):
        """Cannot infer if grandparent has no _target_."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Callback:
            name: str

        store.register("callback", Callback)

        config = {
            "trainer": {
                # No _target_!
                "callbacks": [{"name": "first"}],
            }
        }

        # Act
        result = infer_target_from_parent(config, "trainer.callbacks[0]", store)

        # Assert
        self.assertIsNone(result)

    def test_inferListElement__TooShortPath__ReturnsNone(self):
        """Cannot infer for paths like 'callbacks[0]' without grandparent."""
        # Arrange
        store = self._empty_store()

        config = {
            "callbacks": [{"name": "first"}],
        }

        # Act - Path is just ["callbacks", 0], no grandparent
        result = infer_target_from_parent(config, "callbacks[0]", store)

        # Assert
        self.assertIsNone(result)

    def test_inferListElement__DeeplyNested__Works(self):
        """Infer list element type in deeply nested configs."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Layer:
            size: int

        @dataclass
        class Encoder:
            layers: list[Layer]

        @dataclass
        class Model:
            encoder: Encoder

        store.register("model", Model)
        store.register("encoder", Encoder)
        store.register("layer", Layer)

        config = {
            "model": {
                "_target_": "model",
                "encoder": {
                    "_target_": "encoder",
                    "layers": [{"size": 256}, {"size": 512}],
                },
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.encoder.layers[0]", store)

        # Assert
        self.assertEqual(result, "layer")

    def test_inferListElement__OptionalList__Works(self):
        """Infer element type from Optional[list[X]]."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Callback:
            name: str

        @dataclass
        class Trainer:
            callbacks: Optional[list[Callback]]

        store.register("trainer", Trainer)
        store.register("callback", Callback)

        config = {
            "trainer": {
                "_target_": "trainer",
                "callbacks": [{"name": "first"}],
            }
        }

        # Act
        result = infer_target_from_parent(config, "trainer.callbacks[0]", store)

        # Assert - Optional[list[Callback]] is unwrapped to list[Callback],
        # then element type Callback is extracted
        self.assertEqual(result, "callback")

    def test_inferListElement__NestedListIndex__ReturnsNone(self):
        """Cannot infer for nested list indices like callbacks[0][1]."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Trainer:
            callbacks: list[list]

        store.register("trainer", Trainer)

        config = {
            "trainer": {
                "_target_": "trainer",
                "callbacks": [[{"name": "inner"}]],
            }
        }

        # Act - Path like trainer.callbacks[0][1] not supported
        result = infer_target_from_parent(config, "trainer.callbacks[0][1]", store)

        # Assert
        self.assertIsNone(result)

    def test_inferListElement__NonListField__ReturnsNone(self):
        """Returns None if the field isn't actually a list type."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Trainer:
            config: dict  # Not a list

        store.register("trainer", Trainer)

        config = {
            "trainer": {
                "_target_": "trainer",
                "config": {"key": "value"},
            }
        }

        # Act - Trying to index into a dict field
        result = infer_target_from_parent(config, "trainer.config[0]", store)

        # Assert
        self.assertIsNone(result)

    def test_inferListElement__AutoRegisters__WhenNoTargetExists(self):
        """List element type inference auto-registers if not registered."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Callback:
            name: str

        @dataclass
        class Trainer:
            callbacks: list[Callback]

        store.register("trainer", Trainer)
        # Note: Callback is NOT registered

        config = {
            "trainer": {
                "_target_": "trainer",
                "callbacks": [{"name": "first"}],
            }
        }

        # Act
        result = infer_target_from_parent(config, "trainer.callbacks[0]", store)

        # Assert - should auto-register and return the target name
        self.assertIsNotNone(result)
        self.assertIn("callback", result.lower())


class DictElementTypeInferenceTests(TestCase):
    """Tests for dict element type inference."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def test_inferTargetFromParent__DictValueType__InfersCorrectly(self):
        """Infer value type from dict[str, X] type hint."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            size: int

        @dataclass
        class Registry:
            models: dict[str, Model]

        store.register("registry", Registry)
        store.register("model", Model)

        config = {
            "registry": {
                "_target_": "registry",
                "models": {"resnet": {"size": 256}},
            }
        }

        # Act
        result = infer_target_from_parent(config, 'registry.models["resnet"]', store)

        # Assert
        self.assertEqual(result, "model")

    def test_inferTargetFromParent__DictWithStringKeyPath__InfersValueType(self):
        """Dict inference works with bare string key paths."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            size: int

        @dataclass
        class Registry:
            models: dict[str, Model]

        store.register("registry", Registry)
        store.register("model", Model)

        config = {
            "registry": {
                "_target_": "registry",
                "models": {"vgg": {"size": 512}},
            }
        }

        # Act - using bare key (3 segments: registry, models, vgg)
        result = infer_target_from_parent(config, 'registry.models["vgg"]', store)

        # Assert
        self.assertEqual(result, "model")

    def test_inferTargetFromParent__OptionalDict__InfersValueType(self):
        """Infer value type from Optional[dict[str, X]]."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            size: int

        @dataclass
        class Registry:
            models: Optional[dict[str, Model]]

        store.register("registry", Registry)
        store.register("model", Model)

        config = {
            "registry": {
                "_target_": "registry",
                "models": {"resnet": {"size": 256}},
            }
        }

        # Act
        result = infer_target_from_parent(config, 'registry.models["resnet"]', store)

        # Assert
        self.assertEqual(result, "model")

    def test_inferTargetFromParent__UnparameterizedDict__ReturnsNone(self):
        """Cannot infer from unparameterized dict."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Registry:
            models: dict  # No type parameters

        store.register("registry", Registry)

        config = {
            "registry": {
                "_target_": "registry",
                "models": {"resnet": {"size": 256}},
            }
        }

        # Act
        result = infer_target_from_parent(config, 'registry.models["resnet"]', store)

        # Assert
        self.assertIsNone(result)

    def test_inferTargetFromParent__OptionalDictValueType__InfersAfterUnwrap(self):
        """dict value type Optional[X] is double-unwrapped to infer X."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            size: int

        @dataclass
        class Registry:
            models: dict[str, Optional[Model]]

        store.register("registry", Registry)
        store.register("model", Model)

        config = {
            "registry": {
                "_target_": "registry",
                "models": {"resnet": {"size": 256}},
            }
        }

        # Act
        result = infer_target_from_parent(config, 'registry.models["resnet"]', store)

        # Assert
        self.assertEqual(result, "model")

    def test_inferTargetFromParent__DictPrimitiveValueType__ReturnsNone(self):
        """Cannot infer when dict value type is a primitive."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Registry:
            scores: dict[str, float]

        store.register("registry", Registry)

        config = {
            "registry": {
                "_target_": "registry",
                "scores": {"test": 0.95},
            }
        }

        # Act
        result = infer_target_from_parent(config, 'registry.scores["test"]', store)

        # Assert
        self.assertIsNone(result)


class TupleTypeInferenceTests(TestCase):
    """Tests for tuple positional type inference."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def test_inferTargetFromParent__TuplePositional__InfersCorrectType(self):
        """Infer type from tuple positional type hint."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Encoder:
            hidden_size: int

        @dataclass
        class Decoder:
            output_size: int

        @dataclass
        class Model:
            components: tuple[Encoder, Decoder]

        store.register("model", Model)
        store.register("encoder", Encoder)
        store.register("decoder", Decoder)

        config = {
            "model": {
                "_target_": "model",
                "components": [{"hidden_size": 256}, {"output_size": 128}],
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.components[0]", store)

        # Assert - position 0 is Encoder
        self.assertEqual(result, "encoder")

    def test_inferTargetFromParent__TupleSecondPosition__InfersCorrectType(self):
        """Infer type from second position in tuple."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Encoder:
            hidden_size: int

        @dataclass
        class Decoder:
            output_size: int

        @dataclass
        class Model:
            components: tuple[Encoder, Decoder]

        store.register("model", Model)
        store.register("encoder", Encoder)
        store.register("decoder", Decoder)

        config = {
            "model": {
                "_target_": "model",
                "components": [{"hidden_size": 256}, {"output_size": 128}],
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.components[1]", store)

        # Assert - position 1 is Decoder
        self.assertEqual(result, "decoder")

    def test_inferTargetFromParent__TupleOutOfBounds__ReturnsNone(self):
        """Returns None for index beyond tuple length."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Encoder:
            hidden_size: int

        @dataclass
        class Model:
            components: tuple[Encoder]

        store.register("model", Model)
        store.register("encoder", Encoder)

        config = {
            "model": {
                "_target_": "model",
                "components": [{"hidden_size": 256}, {"hidden_size": 512}],
            }
        }

        # Act - index 1 is out of bounds for tuple[Encoder]
        result = infer_target_from_parent(config, "model.components[1]", store)

        # Assert
        self.assertIsNone(result)

    def test_inferTargetFromParent__TupleVariadic__InfersElementType(self):
        """Infer element type from variadic tuple[X, ...]."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Layer:
            size: int

        @dataclass
        class Model:
            layers: tuple[Layer, ...]

        store.register("model", Model)
        store.register("layer", Layer)

        config = {
            "model": {
                "_target_": "model",
                "layers": [{"size": 256}, {"size": 512}],
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.layers[1]", store)

        # Assert - variadic tuple returns element type for any index
        self.assertEqual(result, "layer")


class AnnotatedTypeInferenceTests(TestCase):
    """Tests for Annotated type unwrapping in inference."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def test_inferTargetFromParent__AnnotatedField__UnwrapsAndInfers(self):
        """Annotated[X, metadata] is unwrapped to X for inference."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Database:
            port: int

        @dataclass
        class Model:
            database: Annotated[Database, "some metadata"]

        store.register("model", Model)
        store.register("database", Database)

        config = {
            "model": {
                "_target_": "model",
                "database": {"port": 5432},
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.database", store)

        # Assert
        self.assertEqual(result, "database")

    def test_inferTargetFromParent__AnnotatedOptionalList__ComposesLayers(self):
        """Annotated[Optional[list[X]], meta] composes all unwrapping layers."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Callback:
            name: str

        @dataclass
        class Trainer:
            callbacks: Annotated[Optional[list[Callback]], "training callbacks"]

        store.register("trainer", Trainer)
        store.register("callback", Callback)

        config = {
            "trainer": {
                "_target_": "trainer",
                "callbacks": [{"name": "first"}],
            }
        }

        # Act
        result = infer_target_from_parent(config, "trainer.callbacks[0]", store)

        # Assert - Annotated -> Optional -> list[Callback] -> Callback
        self.assertEqual(result, "callback")


class OptionalContainerInferenceTests(TestCase):
    """Tests for Optional container type inference."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def test_inferTargetFromParent__OptionalList__InfersElementType(self):
        """Optional[list[X]] is unwrapped to infer element type."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Callback:
            name: str

        @dataclass
        class Trainer:
            callbacks: Optional[list[Callback]]

        store.register("trainer", Trainer)
        store.register("callback", Callback)

        config = {
            "trainer": {
                "_target_": "trainer",
                "callbacks": [{"name": "first"}],
            }
        }

        # Act
        result = infer_target_from_parent(config, "trainer.callbacks[0]", store)

        # Assert
        self.assertEqual(result, "callback")

    def test_inferTargetFromParent__OptionalDictValue__InfersCorrectly(self):
        """Optional[dict[str, X]] is unwrapped to infer value type."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            size: int

        @dataclass
        class Registry:
            models: Optional[dict[str, Model]]

        store.register("registry", Registry)
        store.register("model", Model)

        config = {
            "registry": {
                "_target_": "registry",
                "models": {"resnet": {"size": 256}},
            }
        }

        # Act
        result = infer_target_from_parent(config, 'registry.models["resnet"]', store)

        # Assert
        self.assertEqual(result, "model")


class UnionTypeInferenceTests(TestCase):
    """Tests for union type structural matching in inference."""

    def _empty_store(self) -> TargetRegistry:
        store = TargetRegistry()
        store.clear()
        return store

    def test_inferTargetFromParent__UnionStructuralMatch__InfersCorrectType(self):
        """Union resolved via structural matching of config keys."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class DatabaseA:
            port: int

        @dataclass
        class DatabaseB:
            host: str

        @dataclass
        class Model:
            database: Union[DatabaseA, DatabaseB]

        store.register("model", Model)
        store.register("database_a", DatabaseA)
        store.register("database_b", DatabaseB)

        config = {
            "model": {
                "_target_": "model",
                "database": {"port": 5432},
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.database", store)

        # Assert - DatabaseA has port: int, DatabaseB has host: str
        self.assertEqual(result, "database_a")

    def test_inferTargetFromParent__UnionAmbiguous__ReturnsNone(self):
        """Returns None when multiple union members match config."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class EncoderA:
            size: int

        @dataclass
        class EncoderB:
            size: int

        @dataclass
        class Model:
            encoder: Union[EncoderA, EncoderB]

        store.register("model", Model)
        store.register("encoder_a", EncoderA)
        store.register("encoder_b", EncoderB)

        config = {
            "model": {
                "_target_": "model",
                "encoder": {"size": 256},
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.encoder", store)

        # Assert - both have size: int, ambiguous
        self.assertIsNone(result)

    def test_inferTargetFromParent__UnionNoMatch__ReturnsNone(self):
        """Returns None when no union members match config keys."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class DatabaseA:
            port: int

        @dataclass
        class DatabaseB:
            host: str

        @dataclass
        class Model:
            database: Union[DatabaseA, DatabaseB]

        store.register("model", Model)
        store.register("database_a", DatabaseA)
        store.register("database_b", DatabaseB)

        config = {
            "model": {
                "_target_": "model",
                "database": {"unknown_field": "value"},
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.database", store)

        # Assert - neither DatabaseA nor DatabaseB has unknown_field
        self.assertIsNone(result)

    def test_inferTargetFromParent__UnionWithAbstract__ExpandsSubclasses(self):
        """Abstract union members are expanded to concrete subclasses."""
        # Arrange
        store = self._empty_store()

        class AbstractEncoder(ABC):
            @abstractmethod
            def encode(self) -> None:
                pass

        @dataclass
        class ConcreteEncoder(AbstractEncoder):
            hidden_size: int

            def encode(self) -> None:
                pass

        @dataclass
        class Decoder:
            output_size: int

        @dataclass
        class Model:
            component: Union[AbstractEncoder, Decoder]

        store.register("model", Model)
        store.register("concrete_encoder", ConcreteEncoder)
        store.register("decoder", Decoder)

        config = {
            "model": {
                "_target_": "model",
                "component": {"hidden_size": 256},
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.component", store)

        # Assert - AbstractEncoder expanded to ConcreteEncoder
        self.assertEqual(result, "concrete_encoder")

    def test_inferTargetFromParent__UnionAutoRegisters__WhenNotRegistered(self):
        """Union structural match auto-registers if target not registered."""
        # Arrange
        store = self._empty_store()

        @dataclass
        class DatabaseA:
            port: int

        @dataclass
        class DatabaseB:
            host: str

        @dataclass
        class Model:
            database: Union[DatabaseA, DatabaseB]

        store.register("model", Model)
        # Note: Neither DatabaseA nor DatabaseB is registered

        config = {
            "model": {
                "_target_": "model",
                "database": {"port": 5432},
            }
        }

        # Act
        result = infer_target_from_parent(config, "model.database", store)

        # Assert - should auto-register and return the target name
        self.assertIsNotNone(result)
        self.assertIn("database", result.lower())
