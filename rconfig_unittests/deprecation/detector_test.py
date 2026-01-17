"""Unit tests for DeprecationDetector."""

import warnings
from unittest import TestCase

from rconfig.provenance import ProvenanceBuilder
from rconfig.deprecation.detector import (
    auto_map_deprecated_values,
    check_deprecation,
    handle_deprecated_marker,
    has_deprecated_marker,
)
from rconfig.deprecation.handler import RconfigDeprecationWarning
from rconfig.deprecation.info import DeprecationInfo
from rconfig.deprecation.registry import get_deprecation_registry
from rconfig.errors import DeprecatedKeyError


class CheckDeprecationTests(TestCase):
    """Tests for the check_deprecation function."""

    def setUp(self) -> None:
        self.registry = get_deprecation_registry()
        self.registry.clear()
        self.builder = ProvenanceBuilder()

    def tearDown(self) -> None:
        self.registry.clear()

    def test_checkDeprecation__NotRegistered__ReturnsNone(self):
        # Arrange
        self.builder.add("model.lr", file="config.yaml", line=5)

        # Act
        result = check_deprecation("model.lr", "config.yaml", 5, self.builder)

        # Assert
        self.assertIsNone(result)

    def test_checkDeprecation__Registered__ReturnsInfo(self):
        # Arrange
        self.registry.register("old_key", new_key="new_key")
        self.builder.add("old_key", file="config.yaml", line=5)

        # Act
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = check_deprecation("old_key", "config.yaml", 5, self.builder)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.pattern, "old_key")
        self.assertEqual(result.matched_path, "old_key")
        self.assertEqual(result.new_key, "new_key")

    def test_checkDeprecation__GlobPattern__MatchesAndReturns(self):
        # Arrange
        self.registry.register("**.lr", message="Use optimizer.lr")
        self.builder.add("model.encoder.lr", file="config.yaml", line=10)

        # Act
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = check_deprecation(
                "model.encoder.lr", "config.yaml", 10, self.builder
            )

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.pattern, "**.lr")
        self.assertEqual(result.matched_path, "model.encoder.lr")

    def test_checkDeprecation__RecordsInProvenance__DeprecationSet(self):
        # Arrange
        self.registry.register("old_key", new_key="new_key")
        self.builder.add("old_key", file="config.yaml", line=5)

        # Act
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            check_deprecation("old_key", "config.yaml", 5, self.builder)

        # Assert
        entry = self.builder.get("old_key")
        self.assertIsNotNone(entry.deprecation)
        self.assertEqual(entry.deprecation.new_key, "new_key")

    def test_checkDeprecation__PolicyWarn__EmitsWarning(self):
        # Arrange
        self.registry.register("old_key")
        self.registry.set_policy("warn")
        self.builder.add("old_key", file="config.yaml", line=5)

        # Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_deprecation("old_key", "config.yaml", 5, self.builder)

        # Assert
        self.assertEqual(len(w), 1)
        self.assertTrue(issubclass(w[0].category, RconfigDeprecationWarning))

    def test_checkDeprecation__PolicyError__RaisesException(self):
        # Arrange
        self.registry.register("critical_key", policy="error")
        self.builder.add("critical_key", file="config.yaml", line=5)

        # Act & Assert
        with self.assertRaises(DeprecatedKeyError) as ctx:
            check_deprecation("critical_key", "config.yaml", 5, self.builder)

        self.assertIn("critical_key", str(ctx.exception))

    def test_checkDeprecation__PolicyIgnore__NoWarningOrError(self):
        # Arrange
        self.registry.register("ignored_key")
        self.registry.set_policy("ignore")
        self.builder.add("ignored_key", file="config.yaml", line=5)

        # Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = check_deprecation("ignored_key", "config.yaml", 5, self.builder)

        # Assert - no warnings, but still returns info
        self.assertEqual(len(w), 0)
        self.assertIsNotNone(result)


class HandleDeprecatedMarkerTests(TestCase):
    """Tests for the handle_deprecated_marker function."""

    def setUp(self) -> None:
        self.registry = get_deprecation_registry()
        self.registry.clear()
        self.registry.set_policy("warn")
        self.builder = ProvenanceBuilder()

    def tearDown(self) -> None:
        self.registry.clear()

    def test_handleDeprecatedMarker__NoMarker__ReturnsOriginal(self):
        # Arrange
        value = {"key": "value", "other": 123}
        self.builder.add("test", file="config.yaml", line=1)

        # Act
        result, info = handle_deprecated_marker(
            value, "test", "config.yaml", 1, self.builder
        )

        # Assert
        self.assertEqual(result, value)
        self.assertIsNone(info)

    def test_handleDeprecatedMarker__ShortForm__ParsesMessage(self):
        # Arrange
        value = {
            "_deprecated_": "Use new_param instead",
            "_value_": 42,
        }
        self.builder.add("old_param", file="config.yaml", line=5)

        # Act
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result, info = handle_deprecated_marker(
                value, "old_param", "config.yaml", 5, self.builder
            )

        # Assert
        self.assertEqual(result, 42)
        self.assertIsNotNone(info)
        self.assertEqual(info.message, "Use new_param instead")

    def test_handleDeprecatedMarker__LongForm__ParsesAllFields(self):
        # Arrange
        value = {
            "_deprecated_": {
                "message": "Custom message",
                "new_key": "new.path",
                "remove_in": "2.0.0",
            },
            "_value_": "scalar_value",
        }
        self.builder.add("old_key", file="config.yaml", line=10)

        # Act
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result, info = handle_deprecated_marker(
                value, "old_key", "config.yaml", 10, self.builder
            )

        # Assert
        self.assertEqual(result, "scalar_value")
        self.assertIsNotNone(info)
        self.assertEqual(info.message, "Custom message")
        self.assertEqual(info.new_key, "new.path")
        self.assertEqual(info.remove_in, "2.0.0")

    def test_handleDeprecatedMarker__DictValue__ReturnsWithoutMarker(self):
        # Arrange
        value = {
            "_deprecated_": "Section is deprecated",
            "nested_key": "foo",
            "another": 123,
        }
        self.builder.add("old_section", file="config.yaml", line=5)

        # Act
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result, info = handle_deprecated_marker(
                value, "old_section", "config.yaml", 5, self.builder
            )

        # Assert
        self.assertEqual(result, {"nested_key": "foo", "another": 123})
        self.assertIsNotNone(info)

    def test_handleDeprecatedMarker__RecordsInProvenance__DeprecationSet(self):
        # Arrange
        value = {"_deprecated_": "Deprecated", "_value_": 42}
        self.builder.add("test", file="config.yaml", line=1)

        # Act
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            handle_deprecated_marker(value, "test", "config.yaml", 1, self.builder)

        # Assert
        entry = self.builder.get("test")
        self.assertIsNotNone(entry.deprecation)

    def test_handleDeprecatedMarker__PolicyError__RaisesException(self):
        # Arrange
        self.registry.set_policy("error")
        value = {"_deprecated_": "Critical", "_value_": 42}
        self.builder.add("critical", file="config.yaml", line=1)

        # Act & Assert
        with self.assertRaises(DeprecatedKeyError):
            handle_deprecated_marker(
                value, "critical", "config.yaml", 1, self.builder
            )


class HasDeprecatedMarkerTests(TestCase):
    """Tests for the has_deprecated_marker function."""

    def test_hasDeprecatedMarker__WithMarker__ReturnsTrue(self):
        value = {"_deprecated_": "message", "_value_": 42}

        result = has_deprecated_marker(value)

        self.assertTrue(result)

    def test_hasDeprecatedMarker__WithoutMarker__ReturnsFalse(self):
        value = {"key": "value"}

        result = has_deprecated_marker(value)

        self.assertFalse(result)

    def test_hasDeprecatedMarker__EmptyDict__ReturnsFalse(self):
        value: dict = {}

        result = has_deprecated_marker(value)

        self.assertFalse(result)


class AutoMapDeprecatedValuesTests(TestCase):
    """Tests for the auto_map_deprecated_values function."""

    def setUp(self) -> None:
        self.builder = ProvenanceBuilder()

    def test_autoMap__WithNewKey__CopiesValue(self):
        # Arrange
        config = {"old_key": 42}
        self.builder.add(
            "old_key",
            file="config.yaml",
            line=1,
            deprecation=DeprecationInfo(
                pattern="old_key",
                matched_path="old_key",
                new_key="new_key",
            ),
        )

        # Act
        result = auto_map_deprecated_values(config, self.builder)

        # Assert
        self.assertEqual(result["new_key"], 42)
        self.assertEqual(result["old_key"], 42)  # Old key still exists

    def test_autoMap__NestedNewKey__CreatesIntermediateStructures(self):
        # Arrange
        config = {"learning_rate": 0.001}
        self.builder.add(
            "learning_rate",
            file="config.yaml",
            line=1,
            deprecation=DeprecationInfo(
                pattern="learning_rate",
                matched_path="learning_rate",
                new_key="model.optimizer.lr",
            ),
        )

        # Act
        result = auto_map_deprecated_values(config, self.builder)

        # Assert
        self.assertEqual(result["model"]["optimizer"]["lr"], 0.001)

    def test_autoMap__NewKeyExists__DoesNotOverride(self):
        # Arrange
        config = {
            "old_key": 42,
            "new_key": 100,  # Already exists
        }
        self.builder.add(
            "old_key",
            file="config.yaml",
            line=1,
            deprecation=DeprecationInfo(
                pattern="old_key",
                matched_path="old_key",
                new_key="new_key",
            ),
        )

        # Act
        result = auto_map_deprecated_values(config, self.builder)

        # Assert
        self.assertEqual(result["new_key"], 100)  # Keeps existing value

    def test_autoMap__NoNewKey__DoesNothing(self):
        # Arrange
        config = {"old_key": 42}
        self.builder.add(
            "old_key",
            file="config.yaml",
            line=1,
            deprecation=DeprecationInfo(
                pattern="old_key",
                matched_path="old_key",
                # No new_key
            ),
        )

        # Act
        result = auto_map_deprecated_values(config, self.builder)

        # Assert
        self.assertEqual(result, {"old_key": 42})

    def test_autoMap__NoDeprecation__DoesNothing(self):
        # Arrange
        config = {"key": "value"}
        self.builder.add("key", file="config.yaml", line=1)
        # No deprecation

        # Act
        result = auto_map_deprecated_values(config, self.builder)

        # Assert
        self.assertEqual(result, {"key": "value"})

    def test_autoMap__OldKeyMissing__SkipsGracefully(self):
        # Arrange
        config = {}  # old_key not in config
        self.builder.add(
            "old_key",
            file="config.yaml",
            line=1,
            deprecation=DeprecationInfo(
                pattern="old_key",
                matched_path="old_key",
                new_key="new_key",
            ),
        )

        # Act - should not raise
        result = auto_map_deprecated_values(config, self.builder)

        # Assert
        self.assertEqual(result, {})
