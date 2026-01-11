from abc import ABC
from pathlib import Path
from unittest import TestCase

from rconfig.errors import (
    AmbiguousRefError,
    AmbiguousTargetError,
    CircularInstanceError,
    CircularInterpolationError,
    CircularRefError,
    CompositionError,
    ConfigError,
    ConfigFileError,
    EnvironmentVariableError,
    InstanceResolutionError,
    InstantiationError,
    InterpolationResolutionError,
    InterpolationSyntaxError,
    InvalidInnerPathError,
    InvalidOverridePathError,
    InvalidOverrideSyntaxError,
    MergeError,
    MissingFieldError,
    RefAtRootError,
    RefInstanceConflictError,
    RefResolutionError,
    ResolverExecutionError,
    RequiredValueError,
    TargetNotFoundError,
    TargetTypeMismatchError,
    TypeInferenceError,
    TypeMismatchError,
    UnknownResolverError,
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
        self.assertIn("config", str(error))
        self.assertIn("test.yaml", str(error))
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


class AmbiguousRefErrorTests(TestCase):
    """Tests for AmbiguousRefError."""

    def test_AmbiguousRefError__AllFields__StoresValues(self):
        # Act
        error = AmbiguousRefError(
            ref_path="models/vit",
            found_files=["vit.yaml", "vit.json"],
            config_path="model.encoder",
        )

        # Assert
        self.assertEqual(error.ref_path, "models/vit")
        self.assertEqual(error.found_files, ["vit.yaml", "vit.json"])
        self.assertEqual(error.config_path, "model.encoder")

    def test_AmbiguousRefError__ErrorMessage__ContainsAllFiles(self):
        # Act
        error = AmbiguousRefError(
            ref_path="config",
            found_files=["config.yaml", "config.json", "config.toml"],
        )

        # Assert
        message = str(error)
        self.assertIn("config.yaml", message)
        self.assertIn("config.json", message)
        self.assertIn("config.toml", message)
        self.assertIn("Ambiguous", message)

    def test_AmbiguousRefError__IsCompositionError__InheritsCorrectly(self):
        # Act
        error = AmbiguousRefError("path", ["a.yaml", "a.json"])

        # Assert
        self.assertIsInstance(error, CompositionError)

    def test_AmbiguousRefError__WithConfigPath__IncludesLocation(self):
        # Act
        error = AmbiguousRefError(
            ref_path="model",
            found_files=["model.yaml", "model.json"],
            config_path="trainer.model",
        )

        # Assert
        self.assertIn("at 'trainer.model'", str(error))

    def test_AmbiguousRefError__WithoutConfigPath__OmitsLocation(self):
        # Act
        error = AmbiguousRefError(
            ref_path="model",
            found_files=["model.yaml", "model.json"],
            config_path="",
        )

        # Assert
        self.assertNotIn("at ''", str(error))


class ErrorHintsTests(TestCase):
    """Tests to verify all error types include actionable hints."""

    def test_ConfigFileError__WithHint__IncludesHint(self):
        # Act
        error = ConfigFileError(Path("/test.yaml"), "file not found", hint="Check the path.")

        # Assert
        self.assertIn("Hint:", str(error))
        self.assertIn("Check the path.", str(error))

    def test_ConfigFileError__WithoutHint__NoHintLine(self):
        # Act
        error = ConfigFileError(Path("/test.yaml"), "file not found")

        # Assert
        self.assertNotIn("Hint:", str(error))

    def test_TargetNotFoundError__IncludesHint(self):
        # Act
        error = TargetNotFoundError("unknown", ["a", "b"])

        # Assert
        self.assertIn("Hint:", str(error))
        self.assertIn("register", str(error).lower())

    def test_MissingFieldError__IncludesHint(self):
        # Act
        error = MissingFieldError("field", "target")

        # Assert
        self.assertIn("Hint:", str(error))

    def test_TypeMismatchError__IncludesHint(self):
        # Act
        error = TypeMismatchError("field", int, str)

        # Assert
        self.assertIn("Hint:", str(error))

    def test_InstantiationError__IncludesHint(self):
        # Act
        error = InstantiationError("target", "reason")

        # Assert
        self.assertIn("Hint:", str(error))

    def test_CircularRefError__IncludesHint(self):
        # Act
        error = CircularRefError(["a.yaml", "b.yaml", "a.yaml"])

        # Assert
        self.assertIn("Hint:", str(error))
        self.assertIn("cycle", str(error).lower())

    def test_RefResolutionError__WithHint__IncludesHint(self):
        # Act
        error = RefResolutionError("./file.yaml", "not found", hint="Check the path.")

        # Assert
        self.assertIn("Hint:", str(error))
        self.assertIn("Check the path.", str(error))

    def test_RefAtRootError__IncludesHint(self):
        # Act
        error = RefAtRootError("test.yaml")

        # Assert
        self.assertIn("Hint:", str(error))

    def test_RefInstanceConflictError__IncludesHint(self):
        # Act
        error = RefInstanceConflictError("model")

        # Assert
        self.assertIn("Hint:", str(error))

    def test_InstanceResolutionError__WithHint__IncludesHint(self):
        # Act
        error = InstanceResolutionError("path", "reason", hint="Check syntax.")

        # Assert
        self.assertIn("Hint:", str(error))

    def test_CircularInstanceError__IncludesHint(self):
        # Act
        error = CircularInstanceError(["a", "b", "a"])

        # Assert
        self.assertIn("Hint:", str(error))

    def test_InvalidInnerPathError__IncludesHint(self):
        # Act
        error = InvalidInnerPathError("path", "reason")

        # Assert
        self.assertIn("Hint:", str(error))

    def test_InvalidOverridePathError__IncludesHint(self):
        # Act
        error = InvalidOverridePathError(["model", "lr"], "not found")

        # Assert
        self.assertIn("Hint:", str(error))

    def test_InvalidOverrideSyntaxError__IncludesHint(self):
        # Act
        error = InvalidOverrideSyntaxError("bad=syntax=here", "invalid")

        # Assert
        self.assertIn("Hint:", str(error))

    def test_InterpolationSyntaxError__IncludesHint(self):
        # Act
        error = InterpolationSyntaxError("bad expr", "parse error")

        # Assert
        self.assertIn("Hint:", str(error))

    def test_InterpolationResolutionError__WithHint__IncludesHint(self):
        # Act
        error = InterpolationResolutionError("expr", "reason", hint="Fix it.")

        # Assert
        self.assertIn("Hint:", str(error))
        self.assertIn("Fix it.", str(error))

    def test_CircularInterpolationError__IncludesHint(self):
        # Act
        error = CircularInterpolationError(["a", "b", "a"])

        # Assert
        self.assertIn("Hint:", str(error))

    def test_EnvironmentVariableError__IncludesHint(self):
        # Act
        error = EnvironmentVariableError("MY_VAR")

        # Assert
        self.assertIn("Hint:", str(error))
        self.assertIn("?:", str(error))  # Coalesce operator

    def test_UnknownResolverError__IncludesHint(self):
        # Act
        error = UnknownResolverError("my_resolver", ["uuid", "now"])

        # Assert
        self.assertIn("Hint:", str(error))
        self.assertIn("register_resolver", str(error))

    def test_ResolverExecutionError__IncludesHint(self):
        # Act
        error = ResolverExecutionError("my_resolver", ValueError("bad"))

        # Assert
        self.assertIn("Hint:", str(error))

    def test_RequiredValueError__IncludesHint(self):
        # Act
        error = RequiredValueError([("model.lr", float), ("model.name", str)])

        # Assert
        self.assertIn("Hint:", str(error))

    def test_MergeError__WithHint__IncludesHint(self):
        # Act
        error = MergeError("message", "path", hint="Fix the merge.")

        # Assert
        self.assertIn("Hint:", str(error))
        self.assertIn("Fix the merge.", str(error))

    def test_MergeError__WithoutHint__NoHintLine(self):
        # Act
        error = MergeError("message", "path")

        # Assert
        self.assertNotIn("Hint:", str(error))
