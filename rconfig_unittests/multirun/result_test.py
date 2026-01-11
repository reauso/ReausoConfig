"""Unit tests for MultirunResult."""

from types import MappingProxyType
from unittest import TestCase

from rconfig.multirun import MultirunResult


class MultirunResultTests(TestCase):
    """Tests for the MultirunResult dataclass."""

    def test_MultirunResult__IsFrozen__CannotModifyFields(self):
        # Arrange
        result = MultirunResult(
            config=MappingProxyType({"key": "value"}),
            overrides=MappingProxyType({"lr": 0.01}),
            _instance="instance",
            _error=None,
        )

        # Act & Assert
        with self.assertRaises(AttributeError):
            result.config = MappingProxyType({})  # type: ignore

    def test_MultirunResult__ConfigIsImmutable__RaisesOnModification(self):
        # Arrange
        result = MultirunResult(
            config=MappingProxyType({"key": "value"}),
            overrides=MappingProxyType({}),
            _instance="instance",
            _error=None,
        )

        # Act & Assert
        with self.assertRaises(TypeError):
            result.config["new_key"] = "new_value"  # type: ignore

    def test_MultirunResult__OverridesIsImmutable__RaisesOnModification(self):
        # Arrange
        result = MultirunResult(
            config=MappingProxyType({}),
            overrides=MappingProxyType({"lr": 0.01}),
            _instance="instance",
            _error=None,
        )

        # Act & Assert
        with self.assertRaises(TypeError):
            result.overrides["new_key"] = "new_value"  # type: ignore

    def test_MultirunResult__InstanceProperty__RaisesStoredError(self):
        # Arrange
        error = ValueError("Test error")
        result = MultirunResult(
            config=MappingProxyType({}),
            overrides=MappingProxyType({}),
            _instance=None,
            _error=error,
        )

        # Act & Assert
        with self.assertRaises(ValueError) as ctx:
            _ = result.instance

        self.assertEqual(str(ctx.exception), "Test error")

    def test_MultirunResult__InstanceProperty__ReturnsInstanceOnSuccess(self):
        # Arrange
        instance = {"model": "trained"}
        result = MultirunResult(
            config=MappingProxyType({}),
            overrides=MappingProxyType({}),
            _instance=instance,
            _error=None,
        )

        # Act
        returned = result.instance

        # Assert
        self.assertEqual(returned, instance)

    def test_MultirunResult__Repr__ExcludesPrivateFields(self):
        # Arrange
        result = MultirunResult(
            config=MappingProxyType({"key": "value"}),
            overrides=MappingProxyType({"lr": 0.01}),
            _instance="secret_instance",
            _error=ValueError("secret_error"),
        )

        # Act
        repr_str = repr(result)

        # Assert - _instance and _error should not appear
        self.assertNotIn("_instance", repr_str)
        self.assertNotIn("_error", repr_str)
        self.assertNotIn("secret_instance", repr_str)
        self.assertNotIn("secret_error", repr_str)
        # But config and overrides should appear
        self.assertIn("config", repr_str)
        self.assertIn("overrides", repr_str)
