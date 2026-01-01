from abc import ABC
from pathlib import Path
from unittest.case import TestCase

from rconfig.errors import (
    AmbiguousTargetError,
    ConfigError,
    ConfigFileError,
    InstantiationError,
    MergeError,
    MissingFieldError,
    TargetNotFoundError,
    TargetTypeMismatchError,
    TypeInferenceError,
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


class MergeErrorTests(TestCase):
    def test_MergeError__WithPath__IncludesPathInMessage(self):
        # Act
        error = MergeError("Something went wrong", path="config.model.layers")

        # Assert
        self.assertIsInstance(error, ConfigError)
        self.assertIn("Something went wrong", str(error))
        self.assertIn("config.model.layers", str(error))
        self.assertEqual(error.path, "config.model.layers")

    def test_MergeError__WithoutPath__NoLocationInMessage(self):
        # Act
        error = MergeError("Something went wrong")

        # Assert
        self.assertEqual(str(error), "Something went wrong")
        self.assertEqual(error.path, "")


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


class AmbiguousTargetErrorTests(TestCase):
    def test_AmbiguousTargetError__AbstractClass__FormatsMessageCorrectly(self):
        # Arrange
        class AbstractBase(ABC):
            pass

        # Act
        error = AmbiguousTargetError(
            field="processor",
            expected_type=AbstractBase,
            available_targets=["impl_a", "impl_b"],
            is_abstract=True,
            config_path="pipeline.processor",
        )

        # Assert
        self.assertIsInstance(error, ValidationError)
        message = str(error)
        self.assertIn("processor", message)
        self.assertIn("pipeline.processor", message)
        self.assertIn("abstract", message.lower())
        self.assertIn("'impl_a'", message)
        self.assertIn("'impl_b'", message)
        self.assertIn("_target_", message)

    def test_AmbiguousTargetError__MultipleImplementations__FormatsMessageCorrectly(self):
        # Arrange & Act
        error = AmbiguousTargetError(
            field="encoder",
            expected_type=object,
            available_targets=["enc_a", "enc_b", "enc_c"],
            is_abstract=False,
            config_path="model.encoder",
        )

        # Assert
        message = str(error)
        self.assertIn("multiple", message.lower())
        self.assertIn("_target_", message)
        self.assertIn("'enc_a'", message)
        self.assertIn("'enc_b'", message)
        self.assertIn("'enc_c'", message)

    def test_AmbiguousTargetError__NoAvailableTargets__FormatsMessageCorrectly(self):
        # Arrange & Act
        error = AmbiguousTargetError(
            field="unknown",
            expected_type=object,
            available_targets=[],
            is_abstract=False,
            config_path="",
        )

        # Assert
        message = str(error)
        self.assertIn("none", message.lower())

    def test_AmbiguousTargetError__WithoutConfigPath__OmitsLocation(self):
        # Act
        error = AmbiguousTargetError(
            field="item",
            expected_type=object,
            available_targets=["a"],
            is_abstract=False,
            config_path="",
        )

        # Assert
        self.assertNotIn("at ''", str(error))


class TargetTypeMismatchErrorTests(TestCase):
    def test_TargetTypeMismatchError__FormatsMessageCorrectly(self):
        # Arrange
        class Expected:
            pass

        class Actual:
            pass

        # Act
        error = TargetTypeMismatchError(
            field="encoder",
            target="wrong_target",
            target_class=Actual,
            expected_type=Expected,
            config_path="model.encoder",
        )

        # Assert
        self.assertIsInstance(error, ValidationError)
        message = str(error)
        self.assertIn("encoder", message)
        self.assertIn("wrong_target", message)
        self.assertIn("Expected", message)
        self.assertIn("Actual", message)
        self.assertIn("model.encoder", message)

    def test_TargetTypeMismatchError__WithoutConfigPath__OmitsLocation(self):
        # Arrange
        class A:
            pass

        class B:
            pass

        # Act
        error = TargetTypeMismatchError(
            field="item",
            target="b",
            target_class=B,
            expected_type=A,
            config_path="",
        )

        # Assert
        self.assertNotIn("at ''", str(error))


class TypeInferenceErrorTests(TestCase):
    def test_TypeInferenceError__FormatsMessageWithNestedErrors(self):
        # Arrange
        nested_errors = [
            MissingFieldError("hidden_size", "model", "trainer.model"),
            TypeMismatchError("dropout", float, str, "trainer.model"),
        ]

        class ModelConfig:
            pass

        # Act
        error = TypeInferenceError(
            field="model",
            inferred_type=ModelConfig,
            validation_errors=nested_errors,
            config_path="trainer.model",
        )

        # Assert
        self.assertIsInstance(error, ValidationError)
        message = str(error)
        self.assertIn("model", message)
        self.assertIn("ModelConfig", message)
        self.assertIn("hidden_size", message)
        self.assertIn("_target_", message)

    def test_TypeInferenceError__WithoutConfigPath__OmitsLocation(self):
        # Arrange
        class MyClass:
            pass

        # Act
        error = TypeInferenceError(
            field="item",
            inferred_type=MyClass,
            validation_errors=[],
            config_path="",
        )

        # Assert
        self.assertNotIn("at ''", str(error))
