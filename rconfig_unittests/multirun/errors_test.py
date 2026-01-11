"""Unit tests for multirun error classes."""

from unittest import TestCase

from rconfig.multirun import (
    InvalidSweepValueError,
    NoRunConfigurationError,
    MultirunError,
)
from rconfig.errors import ConfigError


class MultirunErrorTests(TestCase):
    """Tests for MultirunError base class."""

    def test_MultirunError__InheritsFromConfigError(self):
        # Assert
        self.assertTrue(issubclass(MultirunError, ConfigError))


class InvalidSweepValueErrorTests(TestCase):
    """Tests for InvalidSweepValueError."""

    def test_InvalidSweepValueError__Message__ContainsPathAndHint(self):
        # Arrange
        error = InvalidSweepValueError(
            path="callbacks",
            expected="list[list[...]]",
            actual="str",
            index=0,
        )

        # Act
        message = str(error)

        # Assert
        self.assertIn("callbacks", message)
        self.assertIn("index 0", message)
        self.assertIn("list[list[...]]", message)
        self.assertIn("str", message)
        self.assertIn("Hint", message)

    def test_InvalidSweepValueError__AttributesSet(self):
        # Arrange
        error = InvalidSweepValueError(
            path="model.layers",
            expected="list[list[int]]",
            actual="int",
            index=2,
        )

        # Assert
        self.assertEqual(error.path, "model.layers")
        self.assertEqual(error.expected, "list[list[int]]")
        self.assertEqual(error.actual, "int")
        self.assertEqual(error.index, 2)


class NoRunConfigurationErrorTests(TestCase):
    """Tests for NoRunConfigurationError."""

    def test_NoRunConfigurationError__WithOverrides__DescriptiveMessage(self):
        # Arrange
        error = NoRunConfigurationError(has_overrides=True)

        # Act
        message = str(error)

        # Assert
        self.assertIn("No run configuration", message)
        self.assertIn("overrides", message.lower())
        self.assertIn("instantiate()", message)

    def test_NoRunConfigurationError__WithoutOverrides__DescriptiveMessage(self):
        # Arrange
        error = NoRunConfigurationError(has_overrides=False)

        # Act
        message = str(error)

        # Assert
        self.assertIn("No run configuration", message)
        self.assertIn("sweep", message.lower())
        self.assertIn("experiments", message.lower())

    def test_NoRunConfigurationError__AttributeSet(self):
        # Arrange
        error = NoRunConfigurationError(has_overrides=True)

        # Assert
        self.assertTrue(error.has_overrides)
