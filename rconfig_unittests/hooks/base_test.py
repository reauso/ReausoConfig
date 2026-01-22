"""Unit tests for the Callback base class."""

from types import MappingProxyType
from unittest import TestCase

from rconfig.hooks.base import Callback
from rconfig.hooks.models import HookContext, HookPhase


class CallbackTests(TestCase):
    """Tests for the Callback base class."""

    def test_Callback__DefaultMethods__DoNothing(self):
        # Arrange
        callback = Callback()
        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
        )

        # Act & Assert (should not raise)
        callback.on_config_loaded(context)
        callback.on_before_instantiate(context)
        callback.on_after_instantiate(context)
        callback.on_error(context)

    def test_Callback__Subclass__OnConfigLoaded__Called(self):
        # Arrange
        received_context = None

        class TestCallback(Callback):
            def on_config_loaded(self, ctx: HookContext) -> None:
                nonlocal received_context
                received_context = ctx

        callback = TestCallback()
        config = MappingProxyType({"key": "value"})
        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
            config=config,
        )

        # Act
        callback.on_config_loaded(context)

        # Assert
        self.assertIs(received_context, context)

    def test_Callback__Subclass__OnBeforeInstantiate__Called(self):
        # Arrange
        received_context = None

        class TestCallback(Callback):
            def on_before_instantiate(self, ctx: HookContext) -> None:
                nonlocal received_context
                received_context = ctx

        callback = TestCallback()
        context = HookContext(
            phase=HookPhase.BEFORE_INSTANTIATE,
            config_path="config.yaml",
            inner_path="model",
            target_name="model",
        )

        # Act
        callback.on_before_instantiate(context)

        # Assert
        self.assertIs(received_context, context)

    def test_Callback__Subclass__OnAfterInstantiate__Called(self):
        # Arrange
        received_context = None

        class TestCallback(Callback):
            def on_after_instantiate(self, ctx: HookContext) -> None:
                nonlocal received_context
                received_context = ctx

        callback = TestCallback()
        instance = object()
        context = HookContext(
            phase=HookPhase.AFTER_INSTANTIATE,
            config_path="config.yaml",
            inner_path="model",
            target_name="model",
            instance=instance,
        )

        # Act
        callback.on_after_instantiate(context)

        # Assert
        self.assertIs(received_context, context)
        self.assertIs(received_context.instance, instance)

    def test_Callback__Subclass__OnError__Called(self):
        # Arrange
        received_context = None

        class TestCallback(Callback):
            def on_error(self, ctx: HookContext) -> None:
                nonlocal received_context
                received_context = ctx

        callback = TestCallback()
        error = ValueError("test error")
        context = HookContext(
            phase=HookPhase.ON_ERROR,
            config_path="config.yaml",
            error=error,
        )

        # Act
        callback.on_error(context)

        # Assert
        self.assertIs(received_context, context)
        self.assertIs(received_context.error, error)

    def test_Callback__Subclass__PartialOverride__OnlyOverriddenCalled(self):
        # Arrange
        called_methods: list[str] = []

        class PartialCallback(Callback):
            def on_config_loaded(self, ctx: HookContext) -> None:
                called_methods.append("on_config_loaded")

            # on_before_instantiate not overridden
            # on_after_instantiate not overridden
            # on_error not overridden

        callback = PartialCallback()
        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
        )

        # Act
        callback.on_config_loaded(context)
        callback.on_before_instantiate(context)
        callback.on_after_instantiate(context)
        callback.on_error(context)

        # Assert
        self.assertEqual(called_methods, ["on_config_loaded"])

    def test_Callback__Subclass__WithState__MaintainsState(self):
        # Arrange
        class StatefulCallback(Callback):
            def __init__(self):
                self.call_count = 0
                self.configs_seen: list[str] = []

            def on_config_loaded(self, ctx: HookContext) -> None:
                self.call_count += 1
                self.configs_seen.append(ctx.config_path)

        callback = StatefulCallback()

        # Act
        callback.on_config_loaded(
            HookContext(phase=HookPhase.CONFIG_LOADED, config_path="config1.yaml")
        )
        callback.on_config_loaded(
            HookContext(phase=HookPhase.CONFIG_LOADED, config_path="config2.yaml")
        )

        # Assert
        self.assertEqual(callback.call_count, 2)
        self.assertEqual(callback.configs_seen, ["config1.yaml", "config2.yaml"])
