"""Integration tests for the hooks feature.

These tests verify hooks work correctly with real config file instantiation.
"""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest import TestCase

import rconfig as rc
from rconfig.composition import clear_cache
from rconfig.hooks import HookContext, HookPhase, HookRegistry


@dataclass
class ModelConfig:
    hidden_size: int
    dropout: float = 0.1


@dataclass
class TrainerConfig:
    model: ModelConfig
    epochs: int


class HooksIntegrationTests(TestCase):
    """Integration tests for hooks with real config instantiation."""

    def setUp(self) -> None:
        # Clear registries
        rc._store._known_targets.clear()
        HookRegistry().clear()
        clear_cache()

        # Register test targets
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

        # Create temp directory for test configs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        HookRegistry().clear()
        clear_cache()
        self.temp_dir.cleanup()

    def _write_config(self, filename: str, content: str) -> Path:
        """Write a config file and return its path."""
        path = self.config_dir / filename
        path.write_text(content)
        return path

    def test_instantiate__ConfigLoadedHook__ReceivesComposedConfig(self):
        # Arrange
        config_path = self._write_config(
            "model.yaml",
            "_target_: model\nhidden_size: 256\n",
        )

        received_contexts: list[HookContext] = []

        @rc.on_config_loaded
        def capture_config(ctx: HookContext) -> None:
            received_contexts.append(ctx)

        # Act
        rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertEqual(len(received_contexts), 1)
        ctx = received_contexts[0]
        self.assertEqual(ctx.phase, HookPhase.CONFIG_LOADED)
        self.assertEqual(ctx.config_path, str(config_path))
        self.assertIsNotNone(ctx.config)
        self.assertEqual(ctx.config["_target_"], "model")
        self.assertEqual(ctx.config["hidden_size"], 256)

    def test_instantiate__BeforeInstantiateHook__CalledForEachObject(self):
        # Arrange
        config_path = self._write_config(
            "trainer.yaml",
            """
_target_: trainer
epochs: 10
model:
  _target_: model
  hidden_size: 256
""",
        )

        targets_seen: list[str] = []

        @rc.on_before_instantiate
        def capture_targets(ctx: HookContext) -> None:
            targets_seen.append(ctx.target_name)

        # Act
        rc.instantiate(config_path, cli_overrides=False)

        # Assert
        # Should be called for both trainer and nested model
        self.assertEqual(len(targets_seen), 2)
        self.assertIn("model", targets_seen)
        self.assertIn("trainer", targets_seen)

    def test_instantiate__AfterInstantiateHook__ReceivesInstance(self):
        # Arrange
        config_path = self._write_config(
            "model.yaml",
            "_target_: model\nhidden_size: 512\n",
        )

        received_instances: list[tuple[str, object]] = []

        @rc.on_after_instantiate
        def capture_instance(ctx: HookContext) -> None:
            received_instances.append((ctx.target_name, ctx.instance))

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertEqual(len(received_instances), 1)
        target_name, instance = received_instances[0]
        self.assertEqual(target_name, "model")
        self.assertIsInstance(instance, ModelConfig)
        self.assertEqual(instance.hidden_size, 512)
        self.assertIs(instance, result)

    def test_instantiate__NestedConfig__HooksCalledForEachLevel(self):
        # Arrange
        config_path = self._write_config(
            "trainer.yaml",
            """
_target_: trainer
epochs: 10
model:
  _target_: model
  hidden_size: 256
""",
        )

        hook_calls: list[tuple[HookPhase, str]] = []

        @rc.on_before_instantiate
        def before(ctx: HookContext) -> None:
            hook_calls.append((HookPhase.BEFORE_INSTANTIATE, ctx.target_name))

        @rc.on_after_instantiate
        def after(ctx: HookContext) -> None:
            hook_calls.append((HookPhase.AFTER_INSTANTIATE, ctx.target_name))

        # Act
        rc.instantiate(config_path, cli_overrides=False)

        # Assert
        # Nested model is instantiated first, then trainer
        self.assertEqual(len(hook_calls), 4)
        # Model before/after, then Trainer before/after
        self.assertEqual(hook_calls[0], (HookPhase.BEFORE_INSTANTIATE, "model"))
        self.assertEqual(hook_calls[1], (HookPhase.AFTER_INSTANTIATE, "model"))
        self.assertEqual(hook_calls[2], (HookPhase.BEFORE_INSTANTIATE, "trainer"))
        self.assertEqual(hook_calls[3], (HookPhase.AFTER_INSTANTIATE, "trainer"))

    def test_instantiate__ErrorHook__CalledOnFailure(self):
        # Arrange
        config_path = self._write_config(
            "invalid.yaml",
            "_target_: model\n",  # Missing required hidden_size
        )

        received_errors: list[Exception] = []

        @rc.on_error
        def capture_error(ctx: HookContext) -> None:
            received_errors.append(ctx.error)

        # Act & Assert
        with self.assertRaises(Exception):
            rc.instantiate(config_path, cli_overrides=False)

        self.assertEqual(len(received_errors), 1)
        self.assertIsNotNone(received_errors[0])

    def test_instantiate__HookPriority__ExecutesInOrder(self):
        # Arrange
        config_path = self._write_config(
            "model.yaml",
            "_target_: model\nhidden_size: 256\n",
        )

        call_order: list[str] = []

        @rc.on_config_loaded(priority=100)
        def hook_high(ctx: HookContext) -> None:
            call_order.append("high")

        @rc.on_config_loaded(priority=10)
        def hook_low(ctx: HookContext) -> None:
            call_order.append("low")

        @rc.on_config_loaded(priority=50)
        def hook_medium(ctx: HookContext) -> None:
            call_order.append("medium")

        # Act
        rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertEqual(call_order, ["low", "medium", "high"])

    def test_instantiate__PatternFilter__OnlyMatchingHooksCalled(self):
        # Arrange
        models_dir = self.config_dir / "models"
        models_dir.mkdir(exist_ok=True)
        model_config_path = models_dir / "resnet.yaml"
        model_config_path.write_text("_target_: model\nhidden_size: 256\n")

        matched_calls: list[str] = []
        unmatched_calls: list[str] = []

        @rc.on_config_loaded(pattern="**/models/*.yaml")
        def matched_hook(ctx: HookContext) -> None:
            matched_calls.append(ctx.config_path)

        @rc.on_config_loaded(pattern="**/data/*.yaml")
        def unmatched_hook(ctx: HookContext) -> None:
            unmatched_calls.append(ctx.config_path)

        # Act
        rc.instantiate(model_config_path, cli_overrides=False)

        # Assert
        self.assertEqual(len(matched_calls), 1)
        self.assertEqual(len(unmatched_calls), 0)

    def test_instantiate__CallbackClass__AllMethodsCalled(self):
        # Arrange
        config_path = self._write_config(
            "model.yaml",
            "_target_: model\nhidden_size: 256\n",
        )

        class TestCallback(rc.Callback):
            def __init__(self):
                self.calls: list[str] = []

            def on_config_loaded(self, ctx: HookContext) -> None:
                self.calls.append("config_loaded")

            def on_before_instantiate(self, ctx: HookContext) -> None:
                self.calls.append("before_instantiate")

            def on_after_instantiate(self, ctx: HookContext) -> None:
                self.calls.append("after_instantiate")

        callback = TestCallback()
        rc.register_callback(callback)

        # Act
        rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertIn("config_loaded", callback.calls)
        self.assertIn("before_instantiate", callback.calls)
        self.assertIn("after_instantiate", callback.calls)

    def test_validate__Hooks__NotCalled(self):
        # Arrange
        config_path = self._write_config(
            "model.yaml",
            "_target_: model\nhidden_size: 256\n",
        )

        hook_called = False

        @rc.on_config_loaded
        def should_not_be_called(ctx: HookContext) -> None:
            nonlocal hook_called
            hook_called = True

        # Act
        rc.validate(config_path, cli_overrides=False)

        # Assert
        # validate() should NOT invoke hooks - only instantiate() does
        self.assertFalse(hook_called)

    def test_instantiate__InnerPath__HooksReceiveCorrectPaths(self):
        # Arrange
        config_path = self._write_config(
            "trainer.yaml",
            """
_target_: trainer
epochs: 10
model:
  _target_: model
  hidden_size: 256
""",
        )

        config_loaded_paths: list[str] = []
        inner_paths: list[str | None] = []

        @rc.on_config_loaded
        def capture_config_path(ctx: HookContext) -> None:
            config_loaded_paths.append(ctx.config_path)

        @rc.on_before_instantiate
        def capture_inner_path(ctx: HookContext) -> None:
            inner_paths.append(ctx.inner_path)

        # Act
        rc.instantiate(config_path, inner_path="model", cli_overrides=False)

        # Assert
        self.assertEqual(len(config_loaded_paths), 1)
        self.assertEqual(config_loaded_paths[0], str(config_path))
        # When instantiating just the model section via inner_path,
        # only 1 object (model) is instantiated at root level
        self.assertEqual(len(inner_paths), 1)
        # The inner_path in hook context is "" (root) since model was extracted
        self.assertIsNone(inner_paths[0])

    def test_instantiate__ConfigLoadedHookReturnsDict__ConfigModified(self):
        # Arrange
        config_path = self._write_config(
            "model.yaml",
            "_target_: model\nhidden_size: 128\n",
        )

        @rc.on_config_loaded
        def modify_config(ctx: HookContext) -> dict:
            # Return modified config with different hidden_size
            return {**ctx.config, "hidden_size": 512}

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert - model should have the modified value
        self.assertEqual(result.hidden_size, 512)

    def test_instantiate__ConfigLoadedHookInjectsValue__ValueUsedInInstantiation(self):
        # Arrange
        config_path = self._write_config(
            "model.yaml",
            "_target_: model\nhidden_size: 0\ndropout: 0.5\n",
        )

        @rc.on_config_loaded
        def inject_value(ctx: HookContext) -> dict:
            # Simulate injecting a computed/secret value
            config = dict(ctx.config)
            config["hidden_size"] = 256  # Inject the value
            return config

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertEqual(result.hidden_size, 256)
        self.assertEqual(result.dropout, 0.5)  # Other values unchanged

    def test_instantiate__MultipleConfigLoadedHooks__ChainModifications(self):
        # Arrange
        config_path = self._write_config(
            "model.yaml",
            "_target_: model\nhidden_size: 100\n",
        )

        @rc.on_config_loaded(priority=10)
        def first_hook(ctx: HookContext) -> dict:
            # Double the hidden_size
            return {**ctx.config, "hidden_size": ctx.config["hidden_size"] * 2}

        @rc.on_config_loaded(priority=20)
        def second_hook(ctx: HookContext) -> dict:
            # Add 50 to hidden_size
            return {**ctx.config, "hidden_size": ctx.config["hidden_size"] + 50}

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert - (100 * 2) + 50 = 250
        self.assertEqual(result.hidden_size, 250)

    def test_instantiate__ConfigLoadedHookReturnsNone__ConfigUnchanged(self):
        # Arrange
        config_path = self._write_config(
            "model.yaml",
            "_target_: model\nhidden_size: 128\n",
        )

        @rc.on_config_loaded
        def noop_hook(ctx: HookContext) -> None:
            # Hook that doesn't modify config
            pass

        # Act
        result = rc.instantiate(config_path, cli_overrides=False)

        # Assert - original value used
        self.assertEqual(result.hidden_size, 128)
