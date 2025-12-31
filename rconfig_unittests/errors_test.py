from pathlib import Path
from unittest.case import TestCase

from rconfig.errors import (
    ConfigError,
    ConfigFileError,
    InstantiationError,
    MissingFieldError,
    TargetNotFoundError,
    TypeMismatchError,
    ValidationError,
)


class ConfigErrorTests(TestCase):
    def test_ConfigError__IsBaseException__InheritsFromException(self):
        # Act
        error = ConfigError("test message")

        # Assert
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "test message")


class ConfigFileErrorTests(TestCase):
    def test_ConfigFileError__WithPathAndReason__FormatsMessage(self):
        # Arrange
        path = Path("/config/test.yaml")

        # Act
        error = ConfigFileError(path, "file not found")

        # Assert
        self.assertIsInstance(error, ConfigError)
        self.assertEqual(error.path, path)
        self.assertEqual(error.reason, "file not found")
        self.assertIn("/config/test.yaml", str(error))
        self.assertIn("file not found", str(error))


class TargetNotFoundErrorTests(TestCase):
    def test_TargetNotFoundError__WithTargetAndAvailable__FormatsMessage(self):
        # Act
        error = TargetNotFoundError("unknown_target", ["model", "trainer"])

        # Assert
        self.assertIsInstance(error, ConfigError)
        self.assertEqual(error.target, "unknown_target")
        self.assertEqual(error.available, ["model", "trainer"])
        self.assertIn("unknown_target", str(error))
        self.assertIn("'model'", str(error))
        self.assertIn("'trainer'", str(error))

    def test_TargetNotFoundError__WithEmptyAvailable__ShowsNone(self):
        # Act
        error = TargetNotFoundError("unknown_target", [])

        # Assert
        self.assertIn("(none)", str(error))

    def test_TargetNotFoundError__WithConfigPath__IncludesLocation(self):
        # Act
        error = TargetNotFoundError("unknown", ["a"], config_path="model.encoder")

        # Assert
        self.assertEqual(error.config_path, "model.encoder")
        self.assertIn("at 'model.encoder'", str(error))

    def test_TargetNotFoundError__WithoutConfigPath__OmitsLocation(self):
        # Act
        error = TargetNotFoundError("unknown", ["a"])

        # Assert
        self.assertNotIn("at ''", str(error))


class ValidationErrorTests(TestCase):
    def test_ValidationError__IsBaseForValidationErrors__InheritsFromConfigError(self):
        # Act
        error = ValidationError("validation failed", config_path="model")

        # Assert
        self.assertIsInstance(error, ConfigError)
        self.assertEqual(error.config_path, "model")
        self.assertEqual(str(error), "validation failed")


class MissingFieldErrorTests(TestCase):
    def test_MissingFieldError__WithFieldAndTarget__FormatsMessage(self):
        # Act
        error = MissingFieldError("hidden_size", "my_model")

        # Assert
        self.assertIsInstance(error, ValidationError)
        self.assertEqual(error.field, "hidden_size")
        self.assertEqual(error.target, "my_model")
        self.assertIn("hidden_size", str(error))
        self.assertIn("my_model", str(error))

    def test_MissingFieldError__WithConfigPath__IncludesLocation(self):
        # Act
        error = MissingFieldError("size", "model", config_path="trainer.model")

        # Assert
        self.assertEqual(error.config_path, "trainer.model")
        self.assertIn("at 'trainer.model'", str(error))


class TypeMismatchErrorTests(TestCase):
    def test_TypeMismatchError__WithFieldAndTypes__FormatsMessage(self):
        # Act
        error = TypeMismatchError("learning_rate", float, str)

        # Assert
        self.assertIsInstance(error, ValidationError)
        self.assertEqual(error.field, "learning_rate")
        self.assertEqual(error.expected, float)
        self.assertEqual(error.actual, str)
        self.assertIn("learning_rate", str(error))
        self.assertIn("float", str(error))
        self.assertIn("str", str(error))

    def test_TypeMismatchError__WithStringExpected__UsesStringDirectly(self):
        # Act
        error = TypeMismatchError("items", "list[int]", dict)

        # Assert
        self.assertIn("list[int]", str(error))
        self.assertIn("dict", str(error))

    def test_TypeMismatchError__WithConfigPath__IncludesLocation(self):
        # Act
        error = TypeMismatchError("value", int, str, config_path="model.param")

        # Assert
        self.assertEqual(error.config_path, "model.param")
        self.assertIn("at 'model.param'", str(error))


class InstantiationErrorTests(TestCase):
    def test_InstantiationError__WithTargetAndReason__FormatsMessage(self):
        # Act
        error = InstantiationError("my_model", "missing required argument")

        # Assert
        self.assertIsInstance(error, ConfigError)
        self.assertEqual(error.target, "my_model")
        self.assertEqual(error.reason, "missing required argument")
        self.assertIn("my_model", str(error))
        self.assertIn("missing required argument", str(error))

    def test_InstantiationError__WithConfigPath__IncludesLocation(self):
        # Act
        error = InstantiationError("model", "error", config_path="trainer.model")

        # Assert
        self.assertEqual(error.config_path, "trainer.model")
        self.assertIn("at 'trainer.model'", str(error))
