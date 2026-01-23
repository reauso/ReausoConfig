"""Integration tests for enhanced type inference features.

Tests the complete pipeline: dict element, tuple positional, Annotated unwrapping,
Optional container, and union structural matching — all end-to-end through
rc.instantiate() with real YAML config files.
"""

import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping, Sequence
from typing import Annotated, NewType, Optional, Union
from unittest import TestCase

import rconfig as rc


# =============================================================================
# Test dataclasses for dict element inference
# =============================================================================


@dataclass
class OptimizerConfig:
    lr: float
    weight_decay: float = 0.0


@dataclass
class ModelRegistry:
    optimizers: dict[str, OptimizerConfig]


# =============================================================================
# Test dataclasses for tuple positional inference
# =============================================================================


@dataclass
class TupleEncoder:
    hidden_size: int


@dataclass
class TupleDecoder:
    output_size: int


@dataclass
class TupleLoss:
    reduction: str = "mean"


@dataclass
class Pipeline:
    components: tuple[TupleEncoder, TupleDecoder, TupleLoss]


# =============================================================================
# Test dataclasses for Optional container inference
# =============================================================================


@dataclass
class Callback:
    name: str
    priority: int = 0


@dataclass
class OptionalTrainer:
    callbacks: Optional[list[Callback]]
    max_epochs: int = 10


# =============================================================================
# Test dataclasses for Annotated type inference
# =============================================================================


@dataclass
class AnnotatedScheduler:
    step_size: int


@dataclass
class AnnotatedTrainer:
    scheduler: Annotated[AnnotatedScheduler, "learning rate scheduler"]


# =============================================================================
# Test dataclasses for union type inference
# =============================================================================


@dataclass
class SGDOptimizer:
    lr: float
    momentum: float = 0.9


@dataclass
class AdamOptimizer:
    lr: float
    betas: tuple[float, float] = (0.9, 0.999)
    eps: float = 1e-8


@dataclass
class UnionModel:
    optimizer: Union[SGDOptimizer, AdamOptimizer]


# =============================================================================
# Test dataclasses for implicit list element inference
# =============================================================================


@dataclass
class Layer:
    size: int
    activation: str = "relu"


@dataclass
class Network:
    layers: list[Layer]
    name: str = "default"


# =============================================================================
# Test dataclasses for dict value inference
# =============================================================================


@dataclass
class ModelConfig:
    hidden_size: int
    dropout: float = 0.1


@dataclass
class ExperimentRegistry:
    models: dict[str, ModelConfig]


# =============================================================================
# Tests
# =============================================================================


class DictValueInferenceIntegrationTests(TestCase):
    """End-to-end tests for dict value type inference."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        rc._store._known_targets.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_config(self, name: str, content: str) -> Path:
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_instantiate__DictValueInference__InstantiatesCorrectly(self):
        """Dict value type is inferred from dict[str, X] type hint."""
        # Arrange
        rc.register("model_registry", ModelRegistry)
        rc.register("optimizer", OptimizerConfig)

        config_path = self._write_config(
            "config.yaml",
            """
_target_: model_registry
optimizers:
  sgd:
    lr: 0.01
    weight_decay: 0.001
  adam:
    lr: 0.001
""",
        )

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertIsInstance(result, ModelRegistry)
        self.assertIsInstance(result.optimizers["sgd"], OptimizerConfig)
        self.assertEqual(result.optimizers["sgd"].lr, 0.01)
        self.assertEqual(result.optimizers["sgd"].weight_decay, 0.001)
        self.assertIsInstance(result.optimizers["adam"], OptimizerConfig)
        self.assertEqual(result.optimizers["adam"].lr, 0.001)

    def test_instantiate__ImplicitDictValues__InfersFromValueType(self):
        """Dict values without _target_ are inferred from parent's type hint."""
        # Arrange
        rc.register("experiment_registry", ExperimentRegistry)
        rc.register("model_config", ModelConfig)

        config_path = self._write_config(
            "config.yaml",
            """
_target_: experiment_registry
models:
  resnet:
    hidden_size: 512
    dropout: 0.2
  vgg:
    hidden_size: 256
""",
        )

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertIsInstance(result, ExperimentRegistry)
        self.assertIsInstance(result.models["resnet"], ModelConfig)
        self.assertEqual(result.models["resnet"].hidden_size, 512)
        self.assertEqual(result.models["resnet"].dropout, 0.2)
        self.assertIsInstance(result.models["vgg"], ModelConfig)
        self.assertEqual(result.models["vgg"].hidden_size, 256)
        self.assertEqual(result.models["vgg"].dropout, 0.1)


class TuplePositionalInferenceIntegrationTests(TestCase):
    """End-to-end tests for tuple positional type inference.

    Note: YAML has no native tuple syntax, so lists are used in configs.
    Validation is skipped since the validator correctly rejects list-for-tuple.
    The focus here is on type inference and instantiation.
    """

    def setUp(self):
        rc._store._known_targets.clear()

    def test_instantiate__TuplePositionalInference__InstantiatesCorrectly(self):
        """Tuple elements inferred by position from tuple[A, B, C]."""
        # Arrange
        from rconfig.instantiation.Instantiator import ConfigInstantiator
        from rconfig.validation.Validator import ConfigValidator

        rc.register("pipeline", Pipeline)
        rc.register("tuple_encoder", TupleEncoder)
        rc.register("tuple_decoder", TupleDecoder)
        rc.register("tuple_loss", TupleLoss)

        validator = ConfigValidator(rc._store)
        instantiator = ConfigInstantiator(rc._store, validator)
        config = {
            "_target_": "pipeline",
            "components": [
                {"hidden_size": 512},
                {"output_size": 256},
                {"reduction": "sum"},
            ],
        }

        # Act
        result = instantiator.instantiate(config)

        # Assert
        self.assertIsInstance(result, Pipeline)
        self.assertIsInstance(result.components[0], TupleEncoder)
        self.assertEqual(result.components[0].hidden_size, 512)
        self.assertIsInstance(result.components[1], TupleDecoder)
        self.assertEqual(result.components[1].output_size, 256)
        self.assertIsInstance(result.components[2], TupleLoss)
        self.assertEqual(result.components[2].reduction, "sum")


class OptionalContainerInferenceIntegrationTests(TestCase):
    """End-to-end tests for Optional container type inference."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        rc._store._known_targets.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_config(self, name: str, content: str) -> Path:
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_instantiate__OptionalContainerInference__InstantiatesCorrectly(self):
        """Optional[list[X]] unwraps to infer element type."""
        # Arrange
        rc.register("optional_trainer", OptionalTrainer)
        rc.register("callback", Callback)

        config_path = self._write_config(
            "config.yaml",
            """
_target_: optional_trainer
callbacks:
  - name: checkpoint
    priority: 1
  - name: logging
max_epochs: 20
""",
        )

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertIsInstance(result, OptionalTrainer)
        self.assertEqual(result.max_epochs, 20)
        self.assertIsInstance(result.callbacks[0], Callback)
        self.assertEqual(result.callbacks[0].name, "checkpoint")
        self.assertEqual(result.callbacks[0].priority, 1)
        self.assertIsInstance(result.callbacks[1], Callback)
        self.assertEqual(result.callbacks[1].name, "logging")
        self.assertEqual(result.callbacks[1].priority, 0)


class AnnotatedTypeInferenceIntegrationTests(TestCase):
    """End-to-end tests for Annotated type unwrapping."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        rc._store._known_targets.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_config(self, name: str, content: str) -> Path:
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_instantiate__AnnotatedField__UnwrapsAndInstantiates(self):
        """Annotated[X, meta] is unwrapped for type inference."""
        # Arrange
        rc.register("annotated_trainer", AnnotatedTrainer)
        rc.register("annotated_scheduler", AnnotatedScheduler)

        config_path = self._write_config(
            "config.yaml",
            """
_target_: annotated_trainer
scheduler:
  step_size: 10
""",
        )

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertIsInstance(result, AnnotatedTrainer)
        self.assertIsInstance(result.scheduler, AnnotatedScheduler)
        self.assertEqual(result.scheduler.step_size, 10)


class UnionStructuralMatchIntegrationTests(TestCase):
    """End-to-end tests for union structural matching."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        rc._store._known_targets.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_config(self, name: str, content: str) -> Path:
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_instantiate__UnionStructuralMatch__InstantiatesCorrectly(self):
        """Union type resolved via structural matching of config keys."""
        # Arrange
        rc.register("union_model", UnionModel)
        rc.register("sgd", SGDOptimizer)
        rc.register("adam", AdamOptimizer)

        config_path = self._write_config(
            "config.yaml",
            """
_target_: union_model
optimizer:
  lr: 0.01
  momentum: 0.95
""",
        )

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert - momentum is unique to SGDOptimizer
        self.assertIsInstance(result, UnionModel)
        self.assertIsInstance(result.optimizer, SGDOptimizer)
        self.assertEqual(result.optimizer.lr, 0.01)
        self.assertEqual(result.optimizer.momentum, 0.95)

    def test_instantiate__UnionSecondMember__InstantiatesCorrectly(self):
        """Union matches second member when its unique fields are present."""
        # Arrange
        rc.register("union_model", UnionModel)
        rc.register("sgd", SGDOptimizer)
        rc.register("adam", AdamOptimizer)

        config_path = self._write_config(
            "config.yaml",
            """
_target_: union_model
optimizer:
  lr: 0.001
  eps: 0.000001
""",
        )

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert - eps is unique to AdamOptimizer
        self.assertIsInstance(result, UnionModel)
        self.assertIsInstance(result.optimizer, AdamOptimizer)
        self.assertEqual(result.optimizer.lr, 0.001)
        self.assertEqual(result.optimizer.eps, 1e-6)

    def test_instantiate__UnionAutoRegisters__WhenNotRegistered(self):
        """Union structural match auto-registers target if not registered."""
        # Arrange
        rc.register("union_model", UnionModel)
        # Note: SGDOptimizer and AdamOptimizer are NOT registered

        config_path = self._write_config(
            "config.yaml",
            """
_target_: union_model
optimizer:
  lr: 0.01
  momentum: 0.95
""",
        )

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert - should auto-register SGDOptimizer and instantiate
        self.assertIsInstance(result, UnionModel)
        self.assertIsInstance(result.optimizer, SGDOptimizer)
        self.assertEqual(result.optimizer.momentum, 0.95)

    def test_instantiate__UnionAmbiguous__LeavesAsDict(self):
        """Ambiguous union match leaves value as plain dict."""

        # Arrange
        @dataclass
        class OptimizerA:
            lr: float

        @dataclass
        class OptimizerB:
            lr: float

        @dataclass
        class AmbiguousModel:
            optimizer: Union[OptimizerA, OptimizerB]

        rc.register("ambiguous_model", AmbiguousModel)
        rc.register("opt_a", OptimizerA)
        rc.register("opt_b", OptimizerB)

        config_path = self._write_config(
            "config.yaml",
            """
_target_: ambiguous_model
optimizer:
  lr: 0.01
""",
        )

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert - both match, so optimizer stays as dict
        self.assertIsInstance(result, AmbiguousModel)
        self.assertIsInstance(result.optimizer, dict)
        self.assertEqual(result.optimizer["lr"], 0.01)


class ImplicitListElementInferenceIntegrationTests(TestCase):
    """End-to-end tests for implicit list element inference."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        rc._store._known_targets.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_config(self, name: str, content: str) -> Path:
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_instantiate__ImplicitListElements__InfersFromElementType(self):
        """List elements without _target_ are inferred from list[X] type hint."""
        # Arrange
        rc.register("network", Network)
        rc.register("layer", Layer)

        config_path = self._write_config(
            "config.yaml",
            """
_target_: network
name: my_network
layers:
  - size: 256
    activation: relu
  - size: 128
    activation: gelu
  - size: 10
    activation: softmax
""",
        )

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertIsInstance(result, Network)
        self.assertEqual(result.name, "my_network")
        self.assertEqual(len(result.layers), 3)
        for layer in result.layers:
            self.assertIsInstance(layer, Layer)
        self.assertEqual(result.layers[0].size, 256)
        self.assertEqual(result.layers[1].activation, "gelu")
        self.assertEqual(result.layers[2].size, 10)


class UnionWithAbstractIntegrationTests(TestCase):
    """End-to-end tests for union inference with abstract base classes."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        rc._store._known_targets.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_config(self, name: str, content: str) -> Path:
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_instantiate__UnionWithAbstract__ExpandsAndInstantiates(self):
        """Abstract union members are expanded to concrete subclasses."""

        # Arrange
        class AbstractOptimizer(ABC):
            @abstractmethod
            def step(self) -> None:
                pass

        @dataclass
        class ConcreteAdam(AbstractOptimizer):
            lr: float
            eps: float = 1e-8

            def step(self) -> None:
                pass

        @dataclass
        class ConcreteRMSprop(AbstractOptimizer):
            lr: float
            alpha: float = 0.99

            def step(self) -> None:
                pass

        @dataclass
        class AbstractUnionModel:
            optimizer: Union[AbstractOptimizer, TupleLoss]

        rc.register("abstract_union_model", AbstractUnionModel)
        rc.register("concrete_adam", ConcreteAdam)
        rc.register("concrete_rmsprop", ConcreteRMSprop)
        rc.register("tuple_loss", TupleLoss)

        config_path = self._write_config(
            "config.yaml",
            """
_target_: abstract_union_model
optimizer:
  lr: 0.001
  alpha: 0.95
""",
        )

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert - alpha is unique to ConcreteRMSprop
        self.assertIsInstance(result, AbstractUnionModel)
        self.assertIsInstance(result.optimizer, ConcreteRMSprop)
        self.assertEqual(result.optimizer.lr, 0.001)
        self.assertEqual(result.optimizer.alpha, 0.95)


class SetElementInferenceIntegrationTests(TestCase):
    """End-to-end tests for set/frozenset element type inference."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        rc._store._known_targets.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_config(self, name: str, content: str) -> Path:
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_instantiate__SetElementType__InfersCorrectly(self):
        """set[X] element type is inferred from list values in YAML."""

        # Arrange
        @dataclass
        class Tag:
            name: str

        @dataclass
        class Article:
            tags: set[Tag]

        rc.register("article", Article)
        rc.register("tag", Tag)

        config_path = self._write_config(
            "config.yaml",
            """
_target_: article
tags:
  - name: python
  - name: config
""",
        )

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert - YAML list items inferred as Tag via set[Tag] hint
        self.assertIsInstance(result, Article)
        # Result is a list (YAML has no set type), but items are Tag instances
        self.assertEqual(len(result.tags), 2)
        for tag in result.tags:
            self.assertIsInstance(tag, Tag)


class SequenceInferenceIntegrationTests(TestCase):
    """End-to-end tests for Sequence[X] element type inference."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        rc._store._known_targets.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_config(self, name: str, content: str) -> Path:
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_instantiate__SequenceElementType__InfersCorrectly(self):
        """Sequence[X] element type is inferred like list[X]."""

        # Arrange
        @dataclass
        class Step:
            name: str

        @dataclass
        class Pipeline:
            steps: Sequence[Step]

        rc.register("pipeline", Pipeline)
        rc.register("step", Step)

        config_path = self._write_config(
            "config.yaml",
            """
_target_: pipeline
steps:
  - name: preprocess
  - name: train
""",
        )

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertIsInstance(result, Pipeline)
        self.assertEqual(len(result.steps), 2)
        for step in result.steps:
            self.assertIsInstance(step, Step)
        self.assertEqual(result.steps[0].name, "preprocess")


class MappingInferenceIntegrationTests(TestCase):
    """End-to-end tests for Mapping[K, V] value type inference."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        rc._store._known_targets.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_config(self, name: str, content: str) -> Path:
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_instantiate__MappingValueType__InfersCorrectly(self):
        """Mapping[str, X] value type is inferred like dict[str, X]."""

        # Arrange
        @dataclass
        class Endpoint:
            url: str
            port: int = 80

        @dataclass
        class ServiceRegistry:
            services: Mapping[str, Endpoint]

        rc.register("service_registry", ServiceRegistry)
        rc.register("endpoint", Endpoint)

        config_path = self._write_config(
            "config.yaml",
            """
_target_: service_registry
services:
  api:
    url: https://api.example.com
    port: 443
  web:
    url: https://www.example.com
""",
        )

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertIsInstance(result, ServiceRegistry)
        self.assertIsInstance(result.services["api"], Endpoint)
        self.assertIsInstance(result.services["web"], Endpoint)
        self.assertEqual(result.services["api"].port, 443)
        self.assertEqual(result.services["web"].port, 80)


class NewTypeInferenceIntegrationTests(TestCase):
    """End-to-end tests for NewType unwrapping in type inference."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_root = Path(self.temp_dir.name)
        rc._store._known_targets.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_config(self, name: str, content: str) -> Path:
        path = self.config_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_instantiate__NewTypeField__InfersCorrectly(self):
        """NewType wrapping a class is unwrapped for implicit nested inference."""

        # Arrange
        @dataclass
        class DatabaseConnection:
            host: str
            port: int

        DatabaseConfig = NewType("DatabaseConfig", DatabaseConnection)

        @dataclass
        class AppConfig:
            database: DatabaseConfig

        rc.register("app_config", AppConfig)
        rc.register("databaseconnection", DatabaseConnection)

        config_path = self._write_config(
            "config.yaml",
            """
_target_: app_config
database:
  host: localhost
  port: 5432
""",
        )

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertIsInstance(result, AppConfig)
        self.assertIsInstance(result.database, DatabaseConnection)
        self.assertEqual(result.database.host, "localhost")
        self.assertEqual(result.database.port, 5432)
