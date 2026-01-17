"""Integration tests for lazy instantiation feature."""

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest import TestCase

import rconfig as rc
from rconfig.instantiation import is_lazy_proxy, force_initialize


class LazyInstantiationIntegrationTests(TestCase):
    """Full pipeline integration tests for lazy instantiation."""

    def setUp(self):
        rc._store._known_targets.clear()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        rc._store._known_targets.clear()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_yaml(self, name: str, content: str) -> Path:
        path = Path(self.temp_dir) / name
        path.write_text(content)
        return path

    # === Global Lazy Mode ===

    def test_fullPipeline_globalLazy__AllConfigsLazy(self):
        # Arrange
        @dataclass
        class Model:
            hidden_size: int
            dropout: float = 0.1

        @dataclass
        class Trainer:
            model: Model
            epochs: int

        rc.register("model", Model)
        rc.register("trainer", Trainer)

        config_path = self._write_yaml(
            "trainer.yaml",
            """
_target_: trainer
model:
  _target_: model
  hidden_size: 256
epochs: 10
""",
        )

        # Act
        trainer = rc.instantiate(config_path, lazy=True, cli_overrides=False)

        # Assert
        self.assertIsInstance(trainer, Trainer)
        self.assertTrue(is_lazy_proxy(trainer))

        # Access triggers init for outer
        self.assertEqual(trainer.epochs, 10)
        self.assertFalse(is_lazy_proxy(trainer))

        # Inner is still lazy until accessed
        self.assertTrue(is_lazy_proxy(trainer.model))
        self.assertEqual(trainer.model.hidden_size, 256)
        self.assertFalse(is_lazy_proxy(trainer.model))

    def test_fullPipeline_globalLazy__TypeSafe(self):
        # Arrange
        @dataclass
        class Model:
            size: int

        rc.register("model", Model)
        config_path = self._write_yaml(
            "model.yaml",
            """
_target_: model
size: 100
""",
        )

        # Act
        model = rc.instantiate(config_path, Model, lazy=True, cli_overrides=False)

        # Assert - type hint still works
        self.assertIsInstance(model, Model)

    # === Per-Field Lazy Mode ===

    def test_fullPipeline_perFieldLazy__OnlyMarkedLazy(self):
        # Arrange
        @dataclass
        class ExpensiveModel:
            hidden_size: int

        @dataclass
        class CheapOptimizer:
            lr: float

        @dataclass
        class Trainer:
            model: ExpensiveModel
            optimizer: CheapOptimizer

        rc.register("model", ExpensiveModel)
        rc.register("optimizer", CheapOptimizer)
        rc.register("trainer", Trainer)

        config_path = self._write_yaml(
            "trainer.yaml",
            """
_target_: trainer
model:
  _target_: model
  _lazy_: true
  hidden_size: 256
optimizer:
  _target_: optimizer
  lr: 0.001
""",
        )

        # Act
        trainer = rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertTrue(is_lazy_proxy(trainer.model))
        self.assertFalse(is_lazy_proxy(trainer.optimizer))
        self.assertEqual(trainer.optimizer.lr, 0.001)

    def test_fullPipeline_perFieldLazy__NonCascading(self):
        # Arrange
        @dataclass
        class Layer:
            size: int

        @dataclass
        class Encoder:
            layer: Layer

        @dataclass
        class Model:
            encoder: Encoder

        rc.register("layer", Layer)
        rc.register("encoder", Encoder)
        rc.register("model", Model)

        config_path = self._write_yaml(
            "model.yaml",
            """
_target_: model
encoder:
  _target_: encoder
  _lazy_: true
  layer:
    _target_: layer
    size: 512
""",
        )

        # Act
        model = rc.instantiate(config_path, cli_overrides=False)

        # Assert - encoder is lazy, but layer is NOT (non-cascading)
        self.assertTrue(is_lazy_proxy(model.encoder))
        # After accessing encoder, layer should be eager
        layer = model.encoder.layer
        self.assertFalse(is_lazy_proxy(layer))

    # === Lazy with Composition Features ===

    def test_lazy_with_ref__LazyAfterComposition(self):
        # Arrange
        @dataclass
        class BaseModel:
            hidden_size: int

        @dataclass
        class Trainer:
            model: BaseModel

        rc.register("model", BaseModel)
        rc.register("trainer", Trainer)

        self._write_yaml(
            "base_model.yaml",
            """
_target_: model
hidden_size: 128
""",
        )

        config_path = self._write_yaml(
            "trainer.yaml",
            """
_target_: trainer
model:
  _ref_: base_model.yaml
  _lazy_: true
  hidden_size: 256
""",
        )

        # Act
        trainer = rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertTrue(is_lazy_proxy(trainer.model))
        self.assertEqual(trainer.model.hidden_size, 256)  # override applied

    def test_lazy_with_instance__SharedLazyProxy(self):
        # Arrange
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
        class App:
            shared_cache: Cache
            service_a: ServiceA
            service_b: ServiceB

        rc.register("cache", Cache)
        rc.register("service_a", ServiceA)
        rc.register("service_b", ServiceB)
        rc.register("app", App)

        config_path = self._write_yaml(
            "app.yaml",
            """
_target_: app
shared_cache:
  _target_: cache
  _lazy_: true
  size: 100
service_a:
  _target_: service_a
  cache:
    _instance_: shared_cache
service_b:
  _target_: service_b
  cache:
    _instance_: shared_cache
""",
        )

        # Act
        app = rc.instantiate(config_path, cli_overrides=False)

        # Assert - all share the same lazy proxy
        self.assertIs(app.service_a.cache, app.shared_cache)
        self.assertIs(app.service_b.cache, app.shared_cache)
        self.assertTrue(is_lazy_proxy(app.shared_cache))

    def test_lazy_with_interpolation__InterpolationResolvedBeforeLazy(self):
        # Arrange
        @dataclass
        class Model:
            lr: float
            scaled_lr: float

        rc.register("model", Model)

        config_path = self._write_yaml(
            "model.yaml",
            """
_target_: model
_lazy_: true
lr: 0.01
scaled_lr: ${/lr * 10}
""",
        )

        # Act
        model = rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertTrue(is_lazy_proxy(model))
        self.assertEqual(model.lr, 0.01)
        self.assertEqual(model.scaled_lr, 0.1)

    def test_lazy_with_overrides__OverridesApplied(self):
        # Arrange
        @dataclass
        class Model:
            size: int

        rc.register("model", Model)
        config_path = self._write_yaml(
            "model.yaml",
            """
_target_: model
_lazy_: true
size: 100
""",
        )

        # Act
        model = rc.instantiate(
            config_path, overrides={"size": 200}, cli_overrides=False
        )

        # Assert
        self.assertTrue(is_lazy_proxy(model))
        self.assertEqual(model.size, 200)

    # === Utility Functions ===

    def test_is_lazy_proxy__FromPublicAPI(self):
        # Arrange
        @dataclass
        class Model:
            value: int

        rc.register("model", Model)
        config_path = self._write_yaml(
            "model.yaml",
            """
_target_: model
value: 42
""",
        )

        # Act
        model = rc.instantiate(config_path, lazy=True, cli_overrides=False)

        # Assert
        self.assertTrue(rc.is_lazy_proxy(model))
        _ = model.value
        self.assertFalse(rc.is_lazy_proxy(model))

    def test_force_initialize__FromPublicAPI(self):
        # Arrange
        @dataclass
        class Model:
            value: int

        rc.register("model", Model)
        config_path = self._write_yaml(
            "model.yaml",
            """
_target_: model
value: 42
""",
        )

        # Act
        model = rc.instantiate(config_path, lazy=True, cli_overrides=False)
        rc.force_initialize(model)

        # Assert
        self.assertFalse(rc.is_lazy_proxy(model))
        self.assertEqual(model.value, 42)

    # === Partial Instantiation ===

    def test_lazy_with_partial__PartialCanBeLazy(self):
        # Arrange
        @dataclass
        class Model:
            size: int

        @dataclass
        class Trainer:
            model: Model
            epochs: int

        rc.register("model", Model)
        rc.register("trainer", Trainer)

        config_path = self._write_yaml(
            "trainer.yaml",
            """
_target_: trainer
model:
  _target_: model
  size: 256
epochs: 10
""",
        )

        # Act
        model = rc.instantiate(
            config_path, inner_path="model", lazy=True, cli_overrides=False
        )

        # Assert
        self.assertIsInstance(model, Model)
        self.assertTrue(is_lazy_proxy(model))

    # === Deferred Initialization Tracking ===

    def test_lazy__InitNotCalledUntilAccess(self):
        # Arrange
        init_calls = []

        class TrackedModel:
            def __init__(self, value: int):
                init_calls.append(value)
                self.value = value

        rc.register("model", TrackedModel)
        config_path = self._write_yaml(
            "model.yaml",
            """
_target_: model
value: 42
""",
        )

        # Act
        model = rc.instantiate(config_path, lazy=True, cli_overrides=False)

        # Assert - init not called yet
        self.assertEqual(len(init_calls), 0)

        # Access triggers init
        _ = model.value
        self.assertEqual(len(init_calls), 1)
        self.assertEqual(init_calls[0], 42)

    def test_lazy_sharedInstance__InitCalledOnce(self):
        # Arrange
        init_calls = []

        class TrackedCache:
            def __init__(self, size: int):
                init_calls.append(size)
                self.size = size

        @dataclass
        class App:
            cache1: "TrackedCache"
            cache2: "TrackedCache"

        rc.register("cache", TrackedCache)
        rc.register("app", App)

        config_path = self._write_yaml(
            "app.yaml",
            """
_target_: app
cache1:
  _target_: cache
  size: 100
cache2:
  _instance_: cache1
""",
        )

        # Act
        app = rc.instantiate(config_path, lazy=True, cli_overrides=False)

        # Access both caches
        _ = app.cache1.size
        _ = app.cache2.size

        # Assert - init called only once (shared instance)
        self.assertEqual(len(init_calls), 1)
        self.assertIs(app.cache1, app.cache2)


class LazyInstantiationTransparencyIntegrationTests(TestCase):
    """Integration tests verifying lazy proxies are transparent to user code."""

    def setUp(self):
        rc._store._known_targets.clear()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        rc._store._known_targets.clear()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_yaml(self, name: str, content: str) -> Path:
        path = Path(self.temp_dir) / name
        path.write_text(content)
        return path

    def test_lazy_isinstance__WorksWithOriginalClass(self):
        # Arrange
        @dataclass
        class Model:
            value: int

        rc.register("model", Model)
        config_path = self._write_yaml(
            "model.yaml",
            """
_target_: model
value: 42
""",
        )

        # Act
        model = rc.instantiate(config_path, lazy=True, cli_overrides=False)

        # Assert - isinstance works before AND after init
        self.assertIsInstance(model, Model)  # before init
        _ = model.value  # trigger init
        self.assertIsInstance(model, Model)  # after init

    def test_lazy_methodCalls__Work(self):
        # Arrange
        class Calculator:
            def __init__(self, base: int):
                self.base = base

            def add(self, n: int) -> int:
                return self.base + n

            def multiply(self, n: int) -> int:
                return self.base * n

        rc.register("calculator", Calculator)
        config_path = self._write_yaml(
            "calc.yaml",
            """
_target_: calculator
base: 10
""",
        )

        # Act
        calc = rc.instantiate(config_path, lazy=True, cli_overrides=False)

        # Assert - method calls work (trigger init)
        self.assertEqual(calc.add(5), 15)
        self.assertEqual(calc.multiply(3), 30)

    def test_lazy_dataclassAsdict__Works(self):
        # Arrange
        import dataclasses

        @dataclass
        class Model:
            value: int
            name: str

        rc.register("model", Model)
        config_path = self._write_yaml(
            "model.yaml",
            """
_target_: model
value: 42
name: test
""",
        )

        # Act
        model = rc.instantiate(config_path, lazy=True, cli_overrides=False)
        result = dataclasses.asdict(model)

        # Assert
        self.assertEqual(result, {"value": 42, "name": "test"})

    def test_lazy_strAndRepr__Work(self):
        # Arrange
        class Model:
            def __init__(self, value: int):
                self.value = value

            def __str__(self) -> str:
                return f"Model({self.value})"

            def __repr__(self) -> str:
                return f"Model(value={self.value})"

        rc.register("model", Model)
        config_path = self._write_yaml(
            "model.yaml",
            """
_target_: model
value: 42
""",
        )

        # Act
        model = rc.instantiate(config_path, lazy=True, cli_overrides=False)

        # Assert
        self.assertEqual(str(model), "Model(42)")
        self.assertEqual(repr(model), "Model(value=42)")

    def test_lazy_iteration__Works(self):
        # Arrange
        class Container:
            def __init__(self, items: list):
                self.items = items

            def __iter__(self):
                return iter(self.items)

            def __len__(self) -> int:
                return len(self.items)

        rc.register("container", Container)
        config_path = self._write_yaml(
            "container.yaml",
            """
_target_: container
items:
  - 1
  - 2
  - 3
""",
        )

        # Act
        container = rc.instantiate(config_path, lazy=True, cli_overrides=False)

        # Assert
        self.assertEqual(list(container), [1, 2, 3])
        self.assertEqual(len(container), 3)

    def test_lazy_callable__Works(self):
        # Arrange
        class Factory:
            def __init__(self, base: int):
                self.base = base

            def __call__(self, n: int) -> int:
                return self.base + n

        rc.register("factory", Factory)
        config_path = self._write_yaml(
            "factory.yaml",
            """
_target_: factory
base: 10
""",
        )

        # Act
        factory = rc.instantiate(config_path, lazy=True, cli_overrides=False)

        # Assert
        self.assertEqual(factory(5), 15)
