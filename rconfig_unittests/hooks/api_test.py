"""Unit tests for the hooks public API in rconfig/__init__.py."""

from unittest import TestCase

import rconfig as rc
from rconfig.hooks import HookContext, HookPhase, HookRegistry


class HookDecoratorTests(TestCase):
    """Tests for hook decorator functions."""

    def setUp(self) -> None:
        self.registry = HookRegistry()
        self.registry.clear()

    def tearDown(self) -> None:
        self.registry.clear()

    def test_on_config_loaded__NoArgs__RegistersHook(self):
        # Arrange & Act
        @rc.on_config_loaded
        def my_hook(ctx: HookContext) -> None:
            pass

        # Assert
        self.assertIn("my_hook", self.registry)
        hooks = self.registry.known_hooks[HookPhase.CONFIG_LOADED]
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0].name, "my_hook")

    def test_on_config_loaded__WithPriority__RegistersWithPriority(self):
        # Arrange & Act
        @rc.on_config_loaded(priority=10)
        def early_hook(ctx: HookContext) -> None:
            pass

        # Assert
        hooks = self.registry.known_hooks[HookPhase.CONFIG_LOADED]
        self.assertEqual(hooks[0].priority, 10)

    def test_on_config_loaded__WithPattern__RegistersWithPattern(self):
        # Arrange & Act
        @rc.on_config_loaded(pattern="**/model/*.yaml")
        def model_hook(ctx: HookContext) -> None:
            pass

        # Assert
        hooks = self.registry.known_hooks[HookPhase.CONFIG_LOADED]
        self.assertEqual(hooks[0].pattern, "**/model/*.yaml")

    def test_on_config_loaded__ReturnsFunction__FunctionUnchanged(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            return None

        # Act
        result = rc.on_config_loaded(my_hook)

        # Assert
        self.assertIs(result, my_hook)

    def test_on_before_instantiate__NoArgs__RegistersHook(self):
        # Arrange & Act
        @rc.on_before_instantiate
        def my_hook(ctx: HookContext) -> None:
            pass

        # Assert
        hooks = self.registry.known_hooks[HookPhase.BEFORE_INSTANTIATE]
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0].name, "my_hook")

    def test_on_after_instantiate__NoArgs__RegistersHook(self):
        # Arrange & Act
        @rc.on_after_instantiate
        def my_hook(ctx: HookContext) -> None:
            pass

        # Assert
        hooks = self.registry.known_hooks[HookPhase.AFTER_INSTANTIATE]
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0].name, "my_hook")

    def test_on_error__NoArgs__RegistersHook(self):
        # Arrange & Act
        @rc.on_error
        def my_hook(ctx: HookContext) -> None:
            pass

        # Assert
        hooks = self.registry.known_hooks[HookPhase.ON_ERROR]
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0].name, "my_hook")


class RegisterHookTests(TestCase):
    """Tests for rc.register_hook() and rc.unregister_hook()."""

    def setUp(self) -> None:
        self.registry = HookRegistry()
        self.registry.clear()

    def tearDown(self) -> None:
        self.registry.clear()

    def test_register_hook__ValidHook__AddsToRegistry(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        # Act
        rc.register_hook(HookPhase.CONFIG_LOADED, my_hook, name="test_hook")

        # Assert
        self.assertIn("test_hook", self.registry)

    def test_register_hook__WithPattern__StoresPattern(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        # Act
        rc.register_hook(
            HookPhase.CONFIG_LOADED,
            my_hook,
            name="test_hook",
            pattern="*.yaml",
        )

        # Assert
        hooks = self.registry.known_hooks[HookPhase.CONFIG_LOADED]
        self.assertEqual(hooks[0].pattern, "*.yaml")

    def test_unregister_hook__ExistingHook__Removes(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        rc.register_hook(HookPhase.CONFIG_LOADED, my_hook, name="test_hook")

        # Act
        rc.unregister_hook("test_hook")

        # Assert
        self.assertNotIn("test_hook", self.registry)

    def test_unregister_hook__ByPhase__OnlyRemovesFromPhase(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        rc.register_hook(HookPhase.CONFIG_LOADED, my_hook, name="test_hook")
        rc.register_hook(HookPhase.ON_ERROR, my_hook, name="test_hook")

        # Act
        rc.unregister_hook("test_hook", phase=HookPhase.CONFIG_LOADED)

        # Assert
        self.assertEqual(len(self.registry.known_hooks[HookPhase.CONFIG_LOADED]), 0)
        self.assertEqual(len(self.registry.known_hooks[HookPhase.ON_ERROR]), 1)


class RegisterCallbackTests(TestCase):
    """Tests for rc.register_callback() and rc.unregister_callback()."""

    def setUp(self) -> None:
        self.registry = HookRegistry()
        self.registry.clear()

    def tearDown(self) -> None:
        self.registry.clear()

    def test_register_callback__ClassBased__RegistersAllMethods(self):
        # Arrange
        class TestCallback(rc.Callback):
            def on_config_loaded(self, ctx: HookContext) -> None:
                pass

            def on_error(self, ctx: HookContext) -> None:
                pass

        callback = TestCallback()

        # Act
        rc.register_callback(callback)

        # Assert
        # All 4 phases should have a hook registered
        self.assertEqual(len(self.registry.known_hooks[HookPhase.CONFIG_LOADED]), 1)
        self.assertEqual(len(self.registry.known_hooks[HookPhase.BEFORE_INSTANTIATE]), 1)
        self.assertEqual(len(self.registry.known_hooks[HookPhase.AFTER_INSTANTIATE]), 1)
        self.assertEqual(len(self.registry.known_hooks[HookPhase.ON_ERROR]), 1)

    def test_unregister_callback__RemovesAllMethods(self):
        # Arrange
        class TestCallback(rc.Callback):
            pass

        callback = TestCallback()
        rc.register_callback(callback)

        # Act
        rc.unregister_callback(callback)

        # Assert
        for phase in HookPhase:
            self.assertEqual(len(self.registry.known_hooks[phase]), 0)

    def test_register_callback__MultipleCallbacks__AllRegistered(self):
        # Arrange
        class Callback1(rc.Callback):
            pass

        class Callback2(rc.Callback):
            pass

        cb1 = Callback1()
        cb2 = Callback2()

        # Act
        rc.register_callback(cb1)
        rc.register_callback(cb2)

        # Assert
        # Each phase should have 2 hooks (one from each callback)
        self.assertEqual(len(self.registry.known_hooks[HookPhase.CONFIG_LOADED]), 2)


class KnownHooksTests(TestCase):
    """Tests for rc.known_hooks()."""

    def setUp(self) -> None:
        self.registry = HookRegistry()
        self.registry.clear()

    def tearDown(self) -> None:
        self.registry.clear()

    def test_known_hooks__Empty__ReturnsEmptyTuples(self):
        # Act
        hooks = rc.known_hooks()

        # Assert
        for phase in HookPhase:
            self.assertEqual(len(hooks[phase]), 0)

    def test_known_hooks__WithHooks__ReturnsTuples(self):
        # Arrange
        @rc.on_config_loaded
        def hook1(ctx: HookContext) -> None:
            pass

        @rc.on_config_loaded
        def hook2(ctx: HookContext) -> None:
            pass

        # Act
        hooks = rc.known_hooks()

        # Assert
        self.assertEqual(len(hooks[HookPhase.CONFIG_LOADED]), 2)
