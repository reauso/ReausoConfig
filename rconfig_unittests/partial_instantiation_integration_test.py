"""End-to-end integration tests for partial instantiation feature.

These tests cover complex multi-file scenarios with real YAML files.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from unittest import TestCase

import rconfig as rc
from rconfig.composition import clear_cache

from rconfig_unittests.fixtures import MockFileSystem, mock_filesystem


class PartialInstantiationWithRefTests(TestCase):
    """Tests for partial instantiation with _ref_ composition."""

    def setUp(self):
        rc._store.clear()
        clear_cache()

    def test_partial__WithRefComposition__ResolvesRefsFirst(self):
        """Test that _ref_ references are resolved before partial extraction."""

        @dataclass
        class Encoder:
            hidden_size: int
            dropout: float

        @dataclass
        class Model:
            encoder: Encoder

        @dataclass
        class Trainer:
            model: Model
            epochs: int

        rc.register("encoder", Encoder)
        rc.register("model", Model)
        rc.register("trainer", Trainer)

        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/encoder.yaml",
            "_target_: encoder\nhidden_size: 256\ndropout: 0.1\n",
        )
        fs.add_file(
            "/configs/trainer.yaml",
            """
_target_: trainer
model:
  _target_: model
  encoder:
    _ref_: encoder.yaml
    dropout: 0.2
epochs: 10
""",
        )

        with mock_filesystem(fs):
            # Act - partial instantiate the model
            result = rc.instantiate(
                Path("/configs/trainer.yaml"), inner_path="model", cli_overrides=False
            )

            # Assert - _ref_ should be resolved and override applied
            self.assertIsInstance(result, Model)
            self.assertIsInstance(result.encoder, Encoder)
            self.assertEqual(result.encoder.hidden_size, 256)  # From ref
            self.assertEqual(result.encoder.dropout, 0.2)  # Override

    def test_partial__NestedRefs__AllResolved(self):
        """Test partial instantiation with nested _ref_ chains."""

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

        fs = MockFileSystem("/configs")
        fs.add_file("/configs/layer.yaml", "_target_: layer\nsize: 512\n")
        fs.add_file(
            "/configs/encoder.yaml",
            "_target_: encoder\nlayer:\n  _ref_: layer.yaml\n",
        )
        fs.add_file(
            "/configs/model.yaml",
            "_target_: model\nencoder:\n  _ref_: encoder.yaml\n",
        )

        with mock_filesystem(fs):
            # Act
            result = rc.instantiate(
                Path("/configs/model.yaml"), inner_path="encoder", cli_overrides=False
            )

            # Assert
            self.assertIsInstance(result, Encoder)
            self.assertEqual(result.layer.size, 512)


class PartialInstantiationInstanceSharingTests(TestCase):
    """Tests for _instance_ sharing with partial instantiation."""

    def setUp(self):
        rc._store.clear()
        clear_cache()

    def test_partial__MultipleExternalInstances__SharedCorrectly(self):
        """Test that multiple external _instance_ refs share objects."""

        @dataclass
        class Cache:
            name: str

        @dataclass
        class ServiceA:
            cache: Cache

        @dataclass
        class ServiceB:
            cache: Cache

        @dataclass
        class Services:
            a: ServiceA
            b: ServiceB

        @dataclass
        class App:
            shared_cache: Cache
            services: Services

        rc.register("cache", Cache)
        rc.register("service_a", ServiceA)
        rc.register("service_b", ServiceB)
        rc.register("services", Services)
        rc.register("app", App)

        yaml_content = """
_target_: app
shared_cache:
  _target_: cache
  name: shared
services:
  _target_: services
  a:
    _target_: service_a
    cache:
      _instance_: /shared_cache
  b:
    _target_: service_b
    cache:
      _instance_: /shared_cache
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/app.yaml", yaml_content)

        with mock_filesystem(fs):
            # Act - partial instantiate just the services
            result = rc.instantiate(
                Path("/configs/app.yaml"), inner_path="services", cli_overrides=False
            )

            # Assert - both services should share the same cache
            self.assertIs(result.a.cache, result.b.cache)
            self.assertEqual(result.a.cache.name, "shared")

    def test_partial__InternalInstance__SharedWithinPartial(self):
        """Test that _instance_ refs within the partial scope work."""

        @dataclass
        class Encoder:
            dim: int

        @dataclass
        class Decoder:
            encoder: Encoder

        @dataclass
        class Model:
            encoder: Encoder
            decoder: Decoder

        rc.register("encoder", Encoder)
        rc.register("decoder", Decoder)
        rc.register("model", Model)

        yaml_content = """
_target_: model
encoder:
  _target_: encoder
  dim: 512
decoder:
  _target_: decoder
  encoder:
    _instance_: /encoder
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", yaml_content)

        with mock_filesystem(fs):
            # Full instantiation for comparison
            full_result = rc.instantiate(
                Path("/configs/model.yaml"), cli_overrides=False
            )

            # Assert - decoder.encoder should be same object as encoder
            self.assertIs(full_result.decoder.encoder, full_result.encoder)


class PartialInstantiationComplexConfigTests(TestCase):
    """Tests for complex nested configurations with partial instantiation."""

    def setUp(self):
        rc._store.clear()
        clear_cache()

    def test_partial__ComplexNestedConfig__AllLevelsWork(self):
        """Test partial instantiation at various depths of complex config."""

        @dataclass
        class Optimizer:
            lr: float

        @dataclass
        class Scheduler:
            step_size: int

        @dataclass
        class Training:
            optimizer: Optimizer
            scheduler: Scheduler

        @dataclass
        class Layer:
            dim: int

        @dataclass
        class Encoder:
            layers: list

        @dataclass
        class Model:
            encoder: Encoder

        @dataclass
        class Trainer:
            model: Model
            training: Training

        rc.register("optimizer", Optimizer)
        rc.register("scheduler", Scheduler)
        rc.register("training", Training)
        rc.register("layer", Layer)
        rc.register("encoder", Encoder)
        rc.register("model", Model)
        rc.register("trainer", Trainer)

        yaml_content = """
_target_: trainer
model:
  _target_: model
  encoder:
    _target_: encoder
    layers:
      - _target_: layer
        dim: 256
      - _target_: layer
        dim: 512
training:
  _target_: training
  optimizer:
    _target_: optimizer
    lr: 0.001
  scheduler:
    _target_: scheduler
    step_size: 10
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/trainer.yaml", yaml_content)

        with mock_filesystem(fs):
            path = Path("/configs/trainer.yaml")

            # Test various partial paths
            # Level 1: model
            model = rc.instantiate(path, inner_path="model", cli_overrides=False)
            self.assertIsInstance(model, Model)

            # Level 2: model.encoder
            encoder = rc.instantiate(
                path, inner_path="model.encoder", cli_overrides=False
            )
            self.assertIsInstance(encoder, Encoder)
            self.assertEqual(len(encoder.layers), 2)

            # Level 1: training
            training = rc.instantiate(
                path, inner_path="training", cli_overrides=False
            )
            self.assertIsInstance(training, Training)
            self.assertEqual(training.optimizer.lr, 0.001)

            # Level 2: training.scheduler
            scheduler = rc.instantiate(
                path, inner_path="training.scheduler", cli_overrides=False
            )
            self.assertIsInstance(scheduler, Scheduler)
            self.assertEqual(scheduler.step_size, 10)

            # List index: model.encoder.layers[0]
            layer = rc.instantiate(
                path, inner_path="model.encoder.layers[1]", cli_overrides=False
            )
            self.assertIsInstance(layer, Layer)
            self.assertEqual(layer.dim, 512)


class PartialInstantiationWithInterpolationTests(TestCase):
    """Tests for interpolation handling in partial instantiation."""

    def setUp(self):
        rc._store.clear()
        clear_cache()

    def test_partial__InterpolationToDefaults__ResolvesCorrectly(self):
        """Test interpolation to a defaults section works."""

        @dataclass
        class Model:
            hidden_size: int
            vocab_size: int

        @dataclass
        class Config:
            defaults: dict
            model: Model

        rc.register("model", Model)
        rc.register("config", Config)

        yaml_content = """
_target_: config
defaults:
  hidden_size: 768
  vocab_size: 50000
model:
  _target_: model
  hidden_size: ${/defaults.hidden_size}
  vocab_size: ${/defaults.vocab_size}
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/config.yaml", yaml_content)

        with mock_filesystem(fs):
            # Act
            model = rc.instantiate(
                Path("/configs/config.yaml"), inner_path="model", cli_overrides=False
            )

            # Assert - interpolations should be resolved
            self.assertEqual(model.hidden_size, 768)
            self.assertEqual(model.vocab_size, 50000)

    def test_partial__ExpressionInterpolation__ResolvesCorrectly(self):
        """Test expression interpolations work with partial instantiation."""

        @dataclass
        class Model:
            scaled_lr: float
            doubled_size: int

        @dataclass
        class Config:
            base_lr: float
            base_size: int
            model: Model

        rc.register("model", Model)
        rc.register("config", Config)

        yaml_content = """
_target_: config
base_lr: 0.01
base_size: 256
model:
  _target_: model
  scaled_lr: ${/base_lr * 10}
  doubled_size: ${/base_size * 2}
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/config.yaml", yaml_content)

        with mock_filesystem(fs):
            # Act
            model = rc.instantiate(
                Path("/configs/config.yaml"), inner_path="model", cli_overrides=False
            )

            # Assert - expressions should be evaluated
            self.assertAlmostEqual(model.scaled_lr, 0.1)
            self.assertEqual(model.doubled_size, 512)

    def test_partial__EnvVarInterpolation__ResolvesCorrectly(self):
        """Test environment variable interpolations work."""

        @dataclass
        class Model:
            data_path: str

        @dataclass
        class Config:
            model: Model

        rc.register("model", Model)
        rc.register("config", Config)

        yaml_content = """
_target_: config
model:
  _target_: model
  data_path: '${env:TEST_DATA_PATH ?: "/default/path"}'
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/config.yaml", yaml_content)

        try:
            # Set env var
            os.environ["TEST_DATA_PATH"] = "/custom/data/path"

            with mock_filesystem(fs):
                # Act
                model = rc.instantiate(
                    Path("/configs/config.yaml"),
                    inner_path="model",
                    cli_overrides=False,
                )

                # Assert
                self.assertEqual(model.data_path, "/custom/data/path")
        finally:
            del os.environ["TEST_DATA_PATH"]


class PartialInstantiationEdgeCasesTests(TestCase):
    """Tests for edge cases in partial instantiation."""

    def setUp(self):
        rc._store.clear()
        clear_cache()

    def test_partial__EmptyNestedDict__Works(self):
        """Test partial instantiation of config with empty nested dict."""

        @dataclass
        class Model:
            options: dict

        rc.register("model", Model)

        yaml_content = """
_target_: model
options: {}
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.yaml", yaml_content)

        with mock_filesystem(fs):
            # Full instantiation should work
            result = rc.instantiate(Path("/configs/model.yaml"), cli_overrides=False)
            self.assertEqual(result.options, {})

    def test_partial__OptionalNested__Works(self):
        """Test partial instantiation with optional nested fields."""

        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            inner: Optional[Inner] = None

        rc.register("inner", Inner)
        rc.register("outer", Outer)

        yaml_content = """
_target_: outer
inner:
  _target_: inner
  value: 42
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/outer.yaml", yaml_content)

        with mock_filesystem(fs):
            result = rc.instantiate(
                Path("/configs/outer.yaml"), inner_path="inner", cli_overrides=False
            )
            self.assertIsInstance(result, Inner)
            self.assertEqual(result.value, 42)
