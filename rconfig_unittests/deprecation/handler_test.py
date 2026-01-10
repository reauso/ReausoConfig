"""Unit tests for deprecation handlers."""

import warnings
from unittest import TestCase
from unittest.mock import MagicMock, patch

from rconfig.deprecation.handler import (
    DefaultDeprecationHandler,
    DeprecationHandler,
    FunctionDeprecationHandler,
    RconfigDeprecationWarning,
)
from rconfig.deprecation.info import DeprecationInfo


class RconfigDeprecationWarningTests(TestCase):
    """Tests for the RconfigDeprecationWarning class."""

    def test_warning__IsUserWarning__InheritsCorrectly(self):
        # Assert
        self.assertTrue(issubclass(RconfigDeprecationWarning, UserWarning))

    def test_warning__CanBeFiltered__WorksWithWarningsModule(self):
        # Arrange & Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warnings.warn("test", RconfigDeprecationWarning)

        # Assert
        self.assertEqual(len(w), 1)
        self.assertTrue(issubclass(w[0].category, RconfigDeprecationWarning))


class DefaultDeprecationHandlerTests(TestCase):
    """Tests for the DefaultDeprecationHandler class."""

    def setUp(self) -> None:
        self.handler = DefaultDeprecationHandler()

    def test_handle__BasicDeprecation__EmitsWarning(self):
        # Arrange
        info = DeprecationInfo(pattern="old_key")

        # Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.handler.handle(info, "old_key", "config.yaml", 10)

        # Assert
        self.assertEqual(len(w), 1)
        self.assertTrue(issubclass(w[0].category, RconfigDeprecationWarning))
        self.assertIn("old_key", str(w[0].message))

    def test_handle__WithNewKey__IncludesInMessage(self):
        # Arrange
        info = DeprecationInfo(pattern="old_key", new_key="new_key")

        # Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.handler.handle(info, "old_key", "config.yaml", 10)

        # Assert
        self.assertIn("new_key", str(w[0].message))
        self.assertIn("Use 'new_key' instead", str(w[0].message))

    def test_handle__WithMessage__IncludesInMessage(self):
        # Arrange
        info = DeprecationInfo(pattern="old_key", message="Custom message here")

        # Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.handler.handle(info, "old_key", "config.yaml", 10)

        # Assert
        self.assertIn("Custom message here", str(w[0].message))

    def test_handle__WithRemoveIn__IncludesVersion(self):
        # Arrange
        info = DeprecationInfo(pattern="old_key", remove_in="2.0.0")

        # Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.handler.handle(info, "old_key", "config.yaml", 10)

        # Assert
        self.assertIn("2.0.0", str(w[0].message))
        self.assertIn("Will be removed in version", str(w[0].message))

    def test_handle__WithFileAndLine__IncludesLocation(self):
        # Arrange
        info = DeprecationInfo(pattern="old_key")

        # Act
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.handler.handle(info, "old_key", "my_config.yaml", 42)

        # Assert
        self.assertIn("my_config.yaml:42", str(w[0].message))

    def test_formatMessage__AllFields__FormatsCorrectly(self):
        # Arrange
        info = DeprecationInfo(
            pattern="old_key",
            new_key="new_key",
            message="Custom msg",
            remove_in="3.0.0",
        )

        # Act
        result = self.handler._format_message(info, "old_key", "config.yaml", 10)

        # Assert
        self.assertIn("'old_key' is deprecated", result)
        self.assertIn("Use 'new_key' instead", result)
        self.assertIn("Custom msg", result)
        self.assertIn("Will be removed in version 3.0.0", result)
        self.assertIn("(at config.yaml:10)", result)

    def test_formatMessage__MinimalFields__FormatsCorrectly(self):
        # Arrange
        info = DeprecationInfo(pattern="old_key")

        # Act
        result = self.handler._format_message(info, "old_key", "config.yaml", 5)

        # Assert
        self.assertEqual(
            result,
            "'old_key' is deprecated. (at config.yaml:5)"
        )


class FunctionDeprecationHandlerTests(TestCase):
    """Tests for the FunctionDeprecationHandler class."""

    def test_handle__CallsWrappedFunction__WithCorrectArgs(self):
        # Arrange
        mock_func = MagicMock()
        handler = FunctionDeprecationHandler(mock_func)
        info = DeprecationInfo(pattern="old_key", new_key="new_key")

        # Act
        handler.handle(info, "old_key", "config.yaml", 10)

        # Assert
        mock_func.assert_called_once_with(info, "old_key", "config.yaml", 10)

    def test_init__StoresFunction__AccessibleViaAttribute(self):
        # Arrange
        def my_handler(info, path, file, line):
            pass

        # Act
        handler = FunctionDeprecationHandler(my_handler)

        # Assert
        self.assertEqual(handler._func, my_handler)


class DeprecationHandlerAbstractTests(TestCase):
    """Tests for the abstract DeprecationHandler base class."""

    def test_abstract__CannotInstantiate__RaisesTypeError(self):
        # Act & Assert
        with self.assertRaises(TypeError):
            DeprecationHandler()  # type: ignore

    def test_subclass__MustImplementHandle__WorksWhenImplemented(self):
        # Arrange
        class CustomHandler(DeprecationHandler):
            def __init__(self):
                self.calls = []

            def handle(self, info, path, file, line):
                self.calls.append((info, path, file, line))

        handler = CustomHandler()
        info = DeprecationInfo(pattern="test")

        # Act
        handler.handle(info, "test", "file.yaml", 1)

        # Assert
        self.assertEqual(len(handler.calls), 1)
        self.assertEqual(handler.calls[0][1], "test")
