"""Unit tests for hook models."""

from types import MappingProxyType
from unittest import TestCase

from rconfig.hooks.models import HookContext, HookEntry, HookPhase


class HookPhaseTests(TestCase):
    """Tests for the HookPhase enum."""

    def test_HookPhase__AllPhasesExist__EnumComplete(self):
        # Assert
        self.assertIn(HookPhase.CONFIG_LOADED, HookPhase)
        self.assertIn(HookPhase.BEFORE_INSTANTIATE, HookPhase)
        self.assertIn(HookPhase.AFTER_INSTANTIATE, HookPhase)
        self.assertIn(HookPhase.ON_ERROR, HookPhase)
        self.assertEqual(len(HookPhase), 4)

    def test_HookPhase__Name__ReturnsExpectedString(self):
        # Assert
        self.assertEqual(HookPhase.CONFIG_LOADED.name, "CONFIG_LOADED")
        self.assertEqual(HookPhase.BEFORE_INSTANTIATE.name, "BEFORE_INSTANTIATE")
        self.assertEqual(HookPhase.AFTER_INSTANTIATE.name, "AFTER_INSTANTIATE")
        self.assertEqual(HookPhase.ON_ERROR.name, "ON_ERROR")


class HookEntryTests(TestCase):
    """Tests for the HookEntry dataclass."""

    def test_init__AllFields__CreatesEntry(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        # Act
        entry = HookEntry(
            name="test_hook",
            phase=HookPhase.CONFIG_LOADED,
            func=my_hook,
            pattern="**/model/*.yaml",
            priority=10,
        )

        # Assert
        self.assertEqual(entry.name, "test_hook")
        self.assertEqual(entry.phase, HookPhase.CONFIG_LOADED)
        self.assertEqual(entry.func, my_hook)
        self.assertEqual(entry.pattern, "**/model/*.yaml")
        self.assertEqual(entry.priority, 10)

    def test_init__DefaultValues__UsesDefaults(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        # Act
        entry = HookEntry(
            name="test_hook",
            phase=HookPhase.CONFIG_LOADED,
            func=my_hook,
        )

        # Assert
        self.assertIsNone(entry.pattern)
        self.assertEqual(entry.priority, 50)

    def test_frozen__Immutable__CannotModify(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        entry = HookEntry(
            name="test_hook",
            phase=HookPhase.CONFIG_LOADED,
            func=my_hook,
        )

        # Act & Assert
        with self.assertRaises(Exception):  # FrozenInstanceError
            entry.name = "modified"

    def test_frozen__Immutable__CannotModifyPriority(self):
        # Arrange
        def my_hook(ctx: HookContext) -> None:
            pass

        entry = HookEntry(
            name="test_hook",
            phase=HookPhase.CONFIG_LOADED,
            func=my_hook,
        )

        # Act & Assert
        with self.assertRaises(Exception):  # FrozenInstanceError
            entry.priority = 100


class HookContextTests(TestCase):
    """Tests for the HookContext dataclass."""

    def test_init__ConfigLoadedPhase__CreatesContext(self):
        # Arrange
        config = MappingProxyType({"key": "value"})

        # Act
        ctx = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
            config=config,
        )

        # Assert
        self.assertEqual(ctx.phase, HookPhase.CONFIG_LOADED)
        self.assertEqual(ctx.config_path, "config.yaml")
        self.assertEqual(ctx.config, config)
        self.assertIsNone(ctx.inner_path)
        self.assertIsNone(ctx.instance)
        self.assertIsNone(ctx.target_name)
        self.assertIsNone(ctx.error)

    def test_init__BeforeInstantiatePhase__CreatesContext(self):
        # Arrange
        config = MappingProxyType({"_target_": "model"})

        # Act
        ctx = HookContext(
            phase=HookPhase.BEFORE_INSTANTIATE,
            config_path="config.yaml",
            config=config,
            inner_path="model.encoder",
            target_name="encoder",
        )

        # Assert
        self.assertEqual(ctx.phase, HookPhase.BEFORE_INSTANTIATE)
        self.assertEqual(ctx.inner_path, "model.encoder")
        self.assertEqual(ctx.target_name, "encoder")

    def test_init__AfterInstantiatePhase__HasInstance(self):
        # Arrange
        instance = object()
        config = MappingProxyType({"_target_": "model"})

        # Act
        ctx = HookContext(
            phase=HookPhase.AFTER_INSTANTIATE,
            config_path="config.yaml",
            config=config,
            inner_path="model",
            target_name="model",
            instance=instance,
        )

        # Assert
        self.assertEqual(ctx.phase, HookPhase.AFTER_INSTANTIATE)
        self.assertIs(ctx.instance, instance)

    def test_init__OnErrorPhase__HasError(self):
        # Arrange
        error = ValueError("test error")
        config = MappingProxyType({"_target_": "model"})

        # Act
        ctx = HookContext(
            phase=HookPhase.ON_ERROR,
            config_path="config.yaml",
            config=config,
            error=error,
        )

        # Assert
        self.assertEqual(ctx.phase, HookPhase.ON_ERROR)
        self.assertIs(ctx.error, error)

    def test_frozen__Immutable__CannotModify(self):
        # Arrange
        ctx = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
        )

        # Act & Assert
        with self.assertRaises(Exception):  # FrozenInstanceError
            ctx.config_path = "modified.yaml"

    def test_frozen__Immutable__CannotModifyPhase(self):
        # Arrange
        ctx = HookContext(
            phase=HookPhase.CONFIG_LOADED,
            config_path="config.yaml",
        )

        # Act & Assert
        with self.assertRaises(Exception):  # FrozenInstanceError
            ctx.phase = HookPhase.ON_ERROR
