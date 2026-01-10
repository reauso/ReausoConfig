"""Unit tests for DeprecationRegistry."""

from types import MappingProxyType
from unittest import TestCase
from unittest.mock import MagicMock

from rconfig.deprecation.handler import (
    DefaultDeprecationHandler,
    DeprecationHandler,
    FunctionDeprecationHandler,
)
from rconfig.deprecation.info import DeprecationInfo
from rconfig.deprecation.registry import DeprecationRegistry, get_deprecation_registry


class DeprecationRegistryTests(TestCase):
    """Tests for the DeprecationRegistry class."""

    def setUp(self) -> None:
        self.registry = DeprecationRegistry()
        self.registry.clear()  # Ensure clean state for each test

    # === Registration Tests ===

    def test_register__ValidDeprecation__StoresInRegistry(self):
        # Act
        self.registry.register("learning_rate")

        # Assert
        self.assertTrue(self.registry.is_deprecated("learning_rate"))
        info = self.registry.get("learning_rate")
        self.assertIsNotNone(info)
        self.assertEqual(info.pattern, "learning_rate")

    def test_register__WithNewKey__StoresNewKeyMapping(self):
        # Act
        self.registry.register(
            "learning_rate",
            new_key="model.optimizer.lr"
        )

        # Assert
        info = self.registry.get("learning_rate")
        self.assertEqual(info.new_key, "model.optimizer.lr")

    def test_register__WithMessage__StoresMessage(self):
        # Act
        self.registry.register(
            "old_param",
            message="Use new_param instead"
        )

        # Assert
        info = self.registry.get("old_param")
        self.assertEqual(info.message, "Use new_param instead")

    def test_register__WithRemoveIn__StoresVersion(self):
        # Act
        self.registry.register(
            "old_param",
            remove_in="2.0.0"
        )

        # Assert
        info = self.registry.get("old_param")
        self.assertEqual(info.remove_in, "2.0.0")

    def test_register__WithPolicy__StoresPerDeprecationPolicy(self):
        # Act
        self.registry.register(
            "critical_key",
            policy="error"
        )

        # Assert
        info = self.registry.get("critical_key")
        self.assertEqual(info.policy, "error")

    def test_register__WithGlobPattern__StoresPattern(self):
        # Act
        self.registry.register("**.dropout", message="Configured elsewhere")

        # Assert
        self.assertTrue(self.registry.is_deprecated("**.dropout"))
        info = self.registry.get("**.dropout")
        self.assertEqual(info.pattern, "**.dropout")

    def test_register__AllFields__StoresAllCorrectly(self):
        # Act
        self.registry.register(
            "old_key",
            new_key="new_key",
            message="Custom message",
            remove_in="3.0.0",
            policy="warn"
        )

        # Assert
        info = self.registry.get("old_key")
        self.assertEqual(info.pattern, "old_key")
        self.assertEqual(info.new_key, "new_key")
        self.assertEqual(info.message, "Custom message")
        self.assertEqual(info.remove_in, "3.0.0")
        self.assertEqual(info.policy, "warn")

    # === Unregister Tests ===

    def test_unregister__RegisteredKey__RemovesFromRegistry(self):
        # Arrange
        self.registry.register("old_key")

        # Act
        self.registry.unregister("old_key")

        # Assert
        self.assertFalse(self.registry.is_deprecated("old_key"))

    def test_unregister__UnknownKey__RaisesKeyError(self):
        # Act & Assert
        with self.assertRaises(KeyError) as ctx:
            self.registry.unregister("nonexistent")

        self.assertIn("nonexistent", str(ctx.exception))

    # === Lookup Tests ===

    def test_isDeprecated__RegisteredKey__ReturnsTrue(self):
        # Arrange
        self.registry.register("old_key")

        # Act & Assert
        self.assertTrue(self.registry.is_deprecated("old_key"))

    def test_isDeprecated__UnknownKey__ReturnsFalse(self):
        # Act & Assert
        self.assertFalse(self.registry.is_deprecated("unknown_key"))

    def test_get__RegisteredKey__ReturnsDeprecationInfo(self):
        # Arrange
        self.registry.register("old_key", new_key="new_key")

        # Act
        result = self.registry.get("old_key")

        # Assert
        self.assertIsNotNone(result)
        self.assertIsInstance(result, DeprecationInfo)
        self.assertEqual(result.pattern, "old_key")

    def test_get__UnknownKey__ReturnsNone(self):
        # Act
        result = self.registry.get("unknown_key")

        # Assert
        self.assertIsNone(result)

    # === find_match Tests ===

    def test_findMatch__ExactPath__ReturnsInfo(self):
        # Arrange
        self.registry.register("model.lr", new_key="optimizer.lr")

        # Act
        result = self.registry.find_match("model.lr")

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.pattern, "model.lr")

    def test_findMatch__GlobPattern__ReturnsInfo(self):
        # Arrange
        self.registry.register("*.dropout", message="Configured elsewhere")

        # Act
        result = self.registry.find_match("model.dropout")

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.pattern, "*.dropout")

    def test_findMatch__DoubleWildcard__ReturnsInfo(self):
        # Arrange
        self.registry.register("**.hidden_size", message="Use dim instead")

        # Act
        result = self.registry.find_match("model.encoder.hidden_size")

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.pattern, "**.hidden_size")

    def test_findMatch__NoMatch__ReturnsNone(self):
        # Arrange
        self.registry.register("model.lr")

        # Act
        result = self.registry.find_match("model.dropout")

        # Assert
        self.assertIsNone(result)

    def test_findMatch__ExactMatchPriority__ReturnsExact(self):
        # Arrange - register both exact and glob pattern
        self.registry.register("model.lr", new_key="exact_match")
        self.registry.register("*.lr", new_key="glob_match")

        # Act
        result = self.registry.find_match("model.lr")

        # Assert - exact match should be found first
        self.assertIsNotNone(result)
        self.assertEqual(result.new_key, "exact_match")

    # === Policy Tests ===

    def test_setPolicy__ValidPolicy__UpdatesGlobalPolicy(self):
        # Act
        self.registry.set_policy("error")

        # Assert
        self.assertEqual(self.registry.global_policy, "error")

    def test_setPolicy__AllPolicies__WorkCorrectly(self):
        for policy in ["warn", "error", "ignore"]:
            # Act
            self.registry.set_policy(policy)  # type: ignore

            # Assert
            self.assertEqual(self.registry.global_policy, policy)

    def test_effectivePolicy__PerDeprecationSet__UsesPerDeprecation(self):
        # Arrange
        self.registry.set_policy("warn")
        self.registry.register("critical_key", policy="error")
        info = self.registry.get("critical_key")

        # Act
        result = self.registry.effective_policy(info)

        # Assert
        self.assertEqual(result, "error")

    def test_effectivePolicy__PerDeprecationNone__UsesGlobal(self):
        # Arrange
        self.registry.set_policy("error")
        self.registry.register("normal_key")  # No per-deprecation policy
        info = self.registry.get("normal_key")

        # Act
        result = self.registry.effective_policy(info)

        # Assert
        self.assertEqual(result, "error")

    # === Handler Tests ===

    def test_handler__Default__IsDefaultHandler(self):
        # Assert
        self.assertIsInstance(self.registry.handler, DefaultDeprecationHandler)

    def test_setHandler__CustomHandler__UpdatesHandler(self):
        # Arrange
        class CustomHandler(DeprecationHandler):
            def handle(self, info, path, file, line):
                pass

        custom = CustomHandler()

        # Act
        self.registry.set_handler(custom)

        # Assert
        self.assertEqual(self.registry.handler, custom)

    def test_setHandlerFunc__Function__WrapsAsHandler(self):
        # Arrange
        def my_handler(info, path, file, line):
            pass

        # Act
        self.registry.set_handler_func(my_handler)

        # Assert
        self.assertIsInstance(self.registry.handler, FunctionDeprecationHandler)

    # === Properties Tests ===

    def test_knownDeprecations__ReadOnly__ReturnsMappingProxy(self):
        # Arrange
        self.registry.register("key1")
        self.registry.register("key2")

        # Act
        result = self.registry.known_deprecations

        # Assert
        self.assertIsInstance(result, MappingProxyType)
        self.assertEqual(len(result), 2)

    def test_knownDeprecations__ReadOnly__CannotModify(self):
        # Arrange
        self.registry.register("key1")

        # Act & Assert
        with self.assertRaises(TypeError):
            self.registry.known_deprecations["key2"] = DeprecationInfo(pattern="key2")

    # === Clear Tests ===

    def test_clear__WithRegistrations__RemovesAll(self):
        # Arrange
        self.registry.register("key1")
        self.registry.register("key2")
        self.registry.set_policy("error")

        # Act
        self.registry.clear()

        # Assert
        self.assertEqual(len(self.registry.known_deprecations), 0)
        self.assertEqual(self.registry.global_policy, "warn")  # Reset to default
        self.assertIsInstance(self.registry.handler, DefaultDeprecationHandler)


class GetDeprecationRegistryTests(TestCase):
    """Tests for the get_deprecation_registry function."""

    def setUp(self) -> None:
        # Clear registry before each test
        get_deprecation_registry().clear()

    def test_getDeprecationRegistry__ReturnsSingleton__SameInstance(self):
        # Act
        registry1 = get_deprecation_registry()
        registry2 = get_deprecation_registry()

        # Assert
        self.assertIs(registry1, registry2)

    def test_getDeprecationRegistry__HasExpectedMethods__WorksCorrectly(self):
        # Act
        registry = get_deprecation_registry()

        # Assert - check it has the expected methods/attributes
        self.assertTrue(hasattr(registry, "register"))
        self.assertTrue(hasattr(registry, "unregister"))
        self.assertTrue(hasattr(registry, "find_match"))
        self.assertTrue(hasattr(registry, "known_deprecations"))
        self.assertTrue(hasattr(registry, "global_policy"))
