"""Unit tests for HookRegistry."""

import threading
from types import MappingProxyType
from unittest import TestCase
from unittest.mock import MagicMock

from rconfig.errors import HookExecutionError
from rconfig.hooks.models import HookContext, HookPhase
from rconfig.hooks.registry import HookRegistry


class HookRegistryTests(TestCase):
    """Tests for the HookRegistry class."""

    def setUp(self) -> None:
        self.registry = HookRegistry()
        self.registry.clear()

    # === Registration Tests ===

    def test_register__ValidHook__AddsToRegistry(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        # Act
        self.registry.register(HookPhase.CONFIG_LOADED, my_hook, name="test_hook")

        # Assert
        self.assertIn("test_hook", self.registry)
        hooks = self.registry.known_hooks[HookPhase.CONFIG_LOADED]
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0].name, "test_hook")
        self.assertEqual(hooks[0].func, my_hook)

    def test_register__NoName__UsesFunctionName(self):
        # Arrange
        def validate_paths(ctx: HookContext) -> None:
            pass

        # Act
        self.registry.register(HookPhase.CONFIG_LOADED, validate_paths)

        # Assert
        self.assertIn("validate_paths", self.registry)

    def test_register__WithPattern__StoresPattern(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        # Act
        self.registry.register(
            HookPhase.CONFIG_LOADED,
            my_hook,
            name="test_hook",
            pattern="**/model/*.yaml",
        )

        # Assert
        hooks = self.registry.known_hooks[HookPhase.CONFIG_LOADED]
        self.assertEqual(hooks[0].pattern, "**/model/*.yaml")

    def test_register__WithPriority__StoresPriority(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        # Act
        self.registry.register(
            HookPhase.CONFIG_LOADED,
            my_hook,
            name="test_hook",
            priority=10,
        )

        # Assert
        hooks = self.registry.known_hooks[HookPhase.CONFIG_LOADED]
        self.assertEqual(hooks[0].priority, 10)

    def test_register__DuplicateName__OverwritesExisting(self):
        # Arrange
        def first_hook(ctx: HookContext) -> None:
            pass

        def second_hook(ctx: HookContext) -> None:
            pass

        self.registry.register(HookPhase.CONFIG_LOADED, first_hook, name="my_hook")

        # Act
        self.registry.register(HookPhase.CONFIG_LOADED, second_hook, name="my_hook")

        # Assert
        hooks = self.registry.known_hooks[HookPhase.CONFIG_LOADED]
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0].func, second_hook)

    def test_register__NotCallable__RaisesValueError(self):
        # Act & Assert
        with self.assertRaises(ValueError) as ctx:
            self.registry.register(
                HookPhase.CONFIG_LOADED,
                "not a function",  # type: ignore
                name="test_hook",
            )
        self.assertIn("callable", str(ctx.exception).lower())

    def test_register__DifferentPhases__RegistersInCorrectPhase(self):
        # Arrange
        def hook1(ctx: HookContext) -> None:
            pass

        def hook2(ctx: HookContext) -> None:
            pass

        # Act
        self.registry.register(HookPhase.CONFIG_LOADED, hook1, name="hook1")
        self.registry.register(HookPhase.AFTER_INSTANTIATE, hook2, name="hook2")

        # Assert
        self.assertEqual(len(self.registry.known_hooks[HookPhase.CONFIG_LOADED]), 1)
        self.assertEqual(len(self.registry.known_hooks[HookPhase.AFTER_INSTANTIATE]), 1)
        self.assertEqual(len(self.registry.known_hooks[HookPhase.BEFORE_INSTANTIATE]), 0)
        self.assertEqual(len(self.registry.known_hooks[HookPhase.ON_ERROR]), 0)

    # === Unregistration Tests ===

    def test_unregister__ExistingHook__RemovesFromRegistry(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        self.registry.register(HookPhase.CONFIG_LOADED, my_hook, name="test_hook")

        # Act
        self.registry.unregister("test_hook")

        # Assert
        self.assertNotIn("test_hook", self.registry)
        self.assertEqual(len(self.registry.known_hooks[HookPhase.CONFIG_LOADED]), 0)

    def test_unregister__NonExistent__RaisesKeyError(self):
        # Act & Assert
        with self.assertRaises(KeyError):
            self.registry.unregister("nonexistent")

    def test_unregister__ByPhase__OnlyRemovesFromThatPhase(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        self.registry.register(HookPhase.CONFIG_LOADED, my_hook, name="my_hook")
        self.registry.register(HookPhase.ON_ERROR, my_hook, name="my_hook")

        # Act
        self.registry.unregister("my_hook", phase=HookPhase.CONFIG_LOADED)

        # Assert
        self.assertEqual(len(self.registry.known_hooks[HookPhase.CONFIG_LOADED]), 0)
        self.assertEqual(len(self.registry.known_hooks[HookPhase.ON_ERROR]), 1)

    def test_unregister__NoPhase__RemovesFromAllPhases(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        self.registry.register(HookPhase.CONFIG_LOADED, my_hook, name="my_hook")
        self.registry.register(HookPhase.ON_ERROR, my_hook, name="my_hook")

        # Act
        self.registry.unregister("my_hook")

        # Assert
        self.assertNotIn("my_hook", self.registry)
        self.assertEqual(len(self.registry.known_hooks[HookPhase.CONFIG_LOADED]), 0)
        self.assertEqual(len(self.registry.known_hooks[HookPhase.ON_ERROR]), 0)

    # === Invocation Tests ===

    def test_invoke__SingleHook__CallsHookFunction(self):
        # Arrange
        mock_hook = MagicMock()
        self.registry.register(HookPhase.CONFIG_LOADED, mock_hook, name="test_hook")
        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
        )

        # Act
        self.registry.invoke(HookPhase.CONFIG_LOADED, context)

        # Assert
        mock_hook.assert_called_once_with(context)

    def test_invoke__MultipleHooks__CallsInPriorityOrder(self):
        # Arrange
        call_order: list[str] = []

        def hook_low(ctx: HookContext) -> None:
            call_order.append("low")

        def hook_high(ctx: HookContext) -> None:
            call_order.append("high")

        def hook_default(ctx: HookContext) -> None:
            call_order.append("default")

        # Register in non-priority order
        self.registry.register(
            HookPhase.CONFIG_LOADED, hook_high, name="high", priority=100
        )
        self.registry.register(
            HookPhase.CONFIG_LOADED, hook_low, name="low", priority=10
        )
        self.registry.register(
            HookPhase.CONFIG_LOADED, hook_default, name="default", priority=50
        )

        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
        )

        # Act
        self.registry.invoke(HookPhase.CONFIG_LOADED, context)

        # Assert
        self.assertEqual(call_order, ["low", "default", "high"])

    def test_invoke__WithPattern__OnlyCallsMatchingHooks(self):
        # Arrange
        matched_hook = MagicMock()
        unmatched_hook = MagicMock()

        self.registry.register(
            HookPhase.CONFIG_LOADED,
            matched_hook,
            name="matched",
            pattern="**/model/*.yaml",
        )
        self.registry.register(
            HookPhase.CONFIG_LOADED,
            unmatched_hook,
            name="unmatched",
            pattern="**/data/*.yaml",
        )

        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="configs/model/resnet.yaml",
        )

        # Act
        self.registry.invoke(HookPhase.CONFIG_LOADED, context)

        # Assert
        matched_hook.assert_called_once_with(context)
        unmatched_hook.assert_not_called()

    def test_invoke__PatternNoMatch__SkipsHook(self):
        # Arrange
        mock_hook = MagicMock()
        self.registry.register(
            HookPhase.CONFIG_LOADED,
            mock_hook,
            name="test_hook",
            pattern="**/model/*.yaml",
        )

        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="data/train.yaml",
        )

        # Act
        self.registry.invoke(HookPhase.CONFIG_LOADED, context)

        # Assert
        mock_hook.assert_not_called()

    def test_invoke__NoPattern__AlwaysRuns(self):
        # Arrange
        mock_hook = MagicMock()
        self.registry.register(HookPhase.CONFIG_LOADED, mock_hook, name="test_hook")

        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="any/path/config.yaml",
        )

        # Act
        self.registry.invoke(HookPhase.CONFIG_LOADED, context)

        # Assert
        mock_hook.assert_called_once()

    def test_invoke__HookRaises__WrapsInHookExecutionError(self):
        # Arrange
        def failing_hook(ctx: HookContext) -> None:
            raise RuntimeError("Something went wrong")

        self.registry.register(
            HookPhase.CONFIG_LOADED, failing_hook, name="failing_hook"
        )

        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
        )

        # Act & Assert
        with self.assertRaises(HookExecutionError) as ctx:
            self.registry.invoke(HookPhase.CONFIG_LOADED, context)

        self.assertEqual(ctx.exception.hook_name, "failing_hook")
        self.assertEqual(ctx.exception.phase, HookPhase.CONFIG_LOADED)
        self.assertIsInstance(ctx.exception.original_error, RuntimeError)
        self.assertIn("Something went wrong", str(ctx.exception))

    def test_invoke__NoHooks__DoesNothing(self):
        # Arrange
        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
        )

        # Act (should not raise)
        self.registry.invoke(HookPhase.CONFIG_LOADED, context)

    def test_invoke__WrongPhase__DoesNotCallHook(self):
        # Arrange
        mock_hook = MagicMock()
        self.registry.register(HookPhase.CONFIG_LOADED, mock_hook, name="test_hook")

        context = HookContext(
            phase=HookPhase.ON_ERROR,
            config_path="config.yaml",
        )

        # Act
        self.registry.invoke(HookPhase.ON_ERROR, context)

        # Assert
        mock_hook.assert_not_called()

    # === Contains Tests ===

    def test_contains__RegisteredHook__ReturnsTrue(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        self.registry.register(HookPhase.CONFIG_LOADED, my_hook, name="test_hook")

        # Act & Assert
        self.assertTrue("test_hook" in self.registry)

    def test_contains__UnregisteredHook__ReturnsFalse(self):
        # Act & Assert
        self.assertFalse("nonexistent" in self.registry)

    # === Known Hooks Property Tests ===

    def test_known_hooks__Empty__ReturnsEmptyTuples(self):
        # Act
        hooks = self.registry.known_hooks

        # Assert
        self.assertIsInstance(hooks, MappingProxyType)
        for phase in HookPhase:
            self.assertEqual(len(hooks[phase]), 0)
            self.assertIsInstance(hooks[phase], tuple)

    def test_known_hooks__WithHooks__ReturnsTuples(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        self.registry.register(HookPhase.CONFIG_LOADED, my_hook, name="hook1")
        self.registry.register(HookPhase.CONFIG_LOADED, my_hook, name="hook2")

        # Act
        hooks = self.registry.known_hooks

        # Assert
        self.assertEqual(len(hooks[HookPhase.CONFIG_LOADED]), 2)
        self.assertIsInstance(hooks[HookPhase.CONFIG_LOADED], tuple)

    def test_known_hooks__Immutable__CannotModify(self):
        # Arrange
        hooks = self.registry.known_hooks

        # Act & Assert
        with self.assertRaises(TypeError):
            hooks[HookPhase.CONFIG_LOADED] = ()  # type: ignore

    # === Clear Tests ===

    def test_clear__WithHooks__RemovesAllHooks(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        self.registry.register(HookPhase.CONFIG_LOADED, my_hook, name="hook1")
        self.registry.register(HookPhase.ON_ERROR, my_hook, name="hook2")

        # Act
        self.registry.clear()

        # Assert
        for phase in HookPhase:
            self.assertEqual(len(self.registry.known_hooks[phase]), 0)

    # === Thread Safety Tests ===

    def test_register__Concurrent__ThreadSafe(self):
        # Arrange
        errors: list[Exception] = []

        def register_many(prefix: str, count: int) -> None:
            try:
                for i in range(count):

                    def hook(ctx: HookContext, idx: int = i) -> None:
                        pass

                    self.registry.register(
                        HookPhase.CONFIG_LOADED,
                        hook,
                        name=f"{prefix}_{i}",
                    )
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=register_many, args=(f"t{i}", 20))
            for i in range(5)
        ]

        # Act
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert
        self.assertEqual(errors, [])
        self.assertEqual(len(self.registry.known_hooks[HookPhase.CONFIG_LOADED]), 100)


class InvokeWithConfigTests(TestCase):
    """Tests for invoke() with config parameter."""

    def setUp(self) -> None:
        self.registry = HookRegistry()
        self.registry.clear()

    def tearDown(self) -> None:
        self.registry.clear()

    def test_invoke__HookReturnsDict__ConfigUpdated(self):
        # Arrange
        def modify_hook(ctx: HookContext) -> dict:
            return {**ctx.config, "new_key": "new_value"}

        self.registry.register(HookPhase.CONFIG_LOADED, modify_hook, name="modify")
        original_config = {"existing": "value"}
        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
            config=MappingProxyType(original_config),
        )

        # Act
        result = self.registry.invoke(
            HookPhase.CONFIG_LOADED, context, original_config
        )

        # Assert
        self.assertEqual(result["existing"], "value")
        self.assertEqual(result["new_key"], "new_value")

    def test_invoke__HookReturnsNone__ConfigUnchanged(self):
        # Arrange
        def no_return_hook(ctx: HookContext) -> None:
            pass  # Returns None implicitly

        self.registry.register(HookPhase.CONFIG_LOADED, no_return_hook, name="noop")
        original_config = {"key": "value"}
        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
            config=MappingProxyType(original_config),
        )

        # Act
        result = self.registry.invoke(
            HookPhase.CONFIG_LOADED, context, original_config
        )

        # Assert
        self.assertIs(result, original_config)

    def test_invoke__MultipleHooks__ChainModifications(self):
        # Arrange
        def add_a(ctx: HookContext) -> dict:
            return {**ctx.config, "a": 1}

        def add_b(ctx: HookContext) -> dict:
            return {**ctx.config, "b": 2}

        def add_c(ctx: HookContext) -> dict:
            return {**ctx.config, "c": 3}

        self.registry.register(HookPhase.CONFIG_LOADED, add_a, name="add_a", priority=10)
        self.registry.register(HookPhase.CONFIG_LOADED, add_b, name="add_b", priority=20)
        self.registry.register(HookPhase.CONFIG_LOADED, add_c, name="add_c", priority=30)

        original_config: dict = {}
        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
            config=MappingProxyType(original_config),
        )

        # Act
        result = self.registry.invoke(
            HookPhase.CONFIG_LOADED, context, original_config
        )

        # Assert
        self.assertEqual(result, {"a": 1, "b": 2, "c": 3})

    def test_invoke__MixedReturnTypes__OnlyDictUpdates(self):
        # Arrange
        def returns_dict(ctx: HookContext) -> dict:
            return {**ctx.config, "from_dict": True}

        def returns_none(ctx: HookContext) -> None:
            pass

        def returns_string(ctx: HookContext) -> str:
            return "ignored"  # type: ignore

        self.registry.register(HookPhase.CONFIG_LOADED, returns_dict, name="dict", priority=10)
        self.registry.register(HookPhase.CONFIG_LOADED, returns_none, name="none", priority=20)
        self.registry.register(HookPhase.CONFIG_LOADED, returns_string, name="str", priority=30)

        original_config: dict = {}
        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
            config=MappingProxyType(original_config),
        )

        # Act
        result = self.registry.invoke(
            HookPhase.CONFIG_LOADED, context, original_config
        )

        # Assert - only dict return is applied
        self.assertEqual(result, {"from_dict": True})

    def test_invoke__WithConfig__AnyPhaseProcessesReturns(self):
        # Arrange
        def modify_hook(ctx: HookContext) -> dict:
            return {"modified": "value"}

        self.registry.register(HookPhase.BEFORE_INSTANTIATE, modify_hook, name="modify")
        original_config = {"original": "value"}
        context = HookContext(
            phase=HookPhase.BEFORE_INSTANTIATE,
            config_path="config.yaml",
            config=MappingProxyType(original_config),
        )

        # Act
        result = self.registry.invoke(
            HookPhase.BEFORE_INSTANTIATE, context, original_config
        )

        # Assert - when config is passed, dict returns are processed regardless of phase
        self.assertEqual(result, {"modified": "value"})

    def test_invoke__HookSeesUpdatedConfig__ContextUpdatedBetweenHooks(self):
        # Arrange
        seen_configs: list[dict] = []

        def first_hook(ctx: HookContext) -> dict:
            seen_configs.append(dict(ctx.config))
            return {**ctx.config, "first": True}

        def second_hook(ctx: HookContext) -> dict:
            seen_configs.append(dict(ctx.config))
            return {**ctx.config, "second": True}

        self.registry.register(HookPhase.CONFIG_LOADED, first_hook, name="first", priority=10)
        self.registry.register(HookPhase.CONFIG_LOADED, second_hook, name="second", priority=20)

        original_config = {"original": True}
        context = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
            config=MappingProxyType(original_config),
        )

        # Act
        self.registry.invoke(HookPhase.CONFIG_LOADED, context, original_config)

        # Assert - second hook sees the config modified by first hook
        self.assertEqual(seen_configs[0], {"original": True})
        self.assertEqual(seen_configs[1], {"original": True, "first": True})


class HookRegistrySingletonTests(TestCase):
    """Tests for the HookRegistry @Singleton decorator behavior."""

    def test_singleton__MultipleCalls__ReturnsSameInstance(self):
        # Act
        registry1 = HookRegistry()
        registry2 = HookRegistry()

        # Assert
        self.assertIs(registry1, registry2)

    def test_singleton__ReturnsHookRegistryInstance(self):
        # Act
        registry = HookRegistry()

        # Assert
        self.assertIsInstance(registry, HookRegistry.wrapped_class)
