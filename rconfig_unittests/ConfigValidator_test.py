from dataclasses import dataclass
from typing import Optional, Union
from unittest.case import TestCase
from unittest.mock import patch

from rconfig.ConfigStore import ConfigStore
from rconfig.ConfigValidator import ConfigValidator, ValidationResult
from rconfig.errors import MissingFieldError, TargetNotFoundError, TypeMismatchError


class ConfigValidatorTests(TestCase):
    def _empty_store(self) -> ConfigStore:
        store = ConfigStore()
        store._known_references.clear()
        return store

    def test_validate__ValidConfig__ReturnsValidResult(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            hidden_size: int
            dropout: float = 0.1

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "hidden_size": 256}

        # Act
        result = validator.validate(config)

        # Assert
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)

    def test_validate__MissingTarget__ReturnsError(self):
        # Arrange
        store = self._empty_store()
        validator = ConfigValidator(store)
        config = {"hidden_size": 256}

        # Act
        result = validator.validate(config)

        # Assert
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIsInstance(result.errors[0], MissingFieldError)
        self.assertEqual(result.errors[0].field, "_target_")

    def test_validate__UnknownTarget__ReturnsTargetNotFoundError(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            size: int

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "unknown", "size": 256}

        # Act
        result = validator.validate(config)

        # Assert
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIsInstance(result.errors[0], TargetNotFoundError)
        self.assertEqual(result.errors[0].target, "unknown")
        self.assertIn("model", result.errors[0].available)

    def test_validate__MissingRequiredField__ReturnsMissingFieldError(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            required_field: int
            optional_field: str = "default"

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model"}

        # Act
        result = validator.validate(config)

        # Assert
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIsInstance(result.errors[0], MissingFieldError)
        self.assertEqual(result.errors[0].field, "required_field")

    def test_validate__TypeMismatch__ReturnsTypeMismatchError(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            size: int

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "size": "not an int"}

        # Act
        result = validator.validate(config)

        # Assert
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIsInstance(result.errors[0], TypeMismatchError)
        self.assertEqual(result.errors[0].field, "size")

    def test_validate__OptionalFieldWithNone__IsValid(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            value: Optional[int]

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "value": None}

        # Act
        result = validator.validate(config)

        # Assert
        self.assertTrue(result.valid)

    def test_validate__ListField__ValidatesElementTypes(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            layers: list[int]

        store.register("model", Model)
        validator = ConfigValidator(store)

        # Act & Assert - Valid list
        config = {"_target_": "model", "layers": [128, 256, 512]}
        result = validator.validate(config)
        self.assertTrue(result.valid)

        # Act & Assert - Invalid list element type
        config = {"_target_": "model", "layers": [128, "invalid", 512]}
        result = validator.validate(config)
        self.assertFalse(result.valid)

    def test_validate__DictField__ValidatesKeyValueTypes(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            params: dict[str, int]

        store.register("model", Model)
        validator = ConfigValidator(store)

        # Act & Assert - Valid dict
        config = {"_target_": "model", "params": {"a": 1, "b": 2}}
        result = validator.validate(config)
        self.assertTrue(result.valid)

        # Act & Assert - Invalid dict value type
        config = {"_target_": "model", "params": {"a": "not int"}}
        result = validator.validate(config)
        self.assertFalse(result.valid)

    def test_validate__NestedConfig__ValidatesRecursively(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class InnerModel:
            size: int

        @dataclass
        class OuterModel:
            inner: InnerModel

        store.register("inner", InnerModel)
        store.register("outer", OuterModel)
        validator = ConfigValidator(store)
        config = {
            "_target_": "outer",
            "inner": {"_target_": "inner", "size": 256},
        }

        # Act
        result = validator.validate(config)

        # Assert
        self.assertTrue(result.valid)

    def test_validate__NestedConfigWithError__ReturnsNestedError(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class InnerModel:
            size: int

        @dataclass
        class OuterModel:
            inner: InnerModel

        store.register("inner", InnerModel)
        store.register("outer", OuterModel)
        validator = ConfigValidator(store)
        config = {
            "_target_": "outer",
            "inner": {"_target_": "inner"},  # Missing required 'size'
        }

        # Act
        result = validator.validate(config)

        # Assert
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIsInstance(result.errors[0], MissingFieldError)
        self.assertEqual(result.errors[0].field, "size")
        self.assertEqual(result.errors[0].config_path, "inner")

    def test_validate__WithConfigPath__IncludesPathInErrors(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            size: int

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model"}

        # Act
        result = validator.validate(config, config_path="trainer.model")

        # Assert
        self.assertFalse(result.valid)
        self.assertEqual(result.errors[0].config_path, "trainer.model")

    def test_validate__MultipleErrors__ReturnsAllErrors(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            a: int
            b: str
            c: float

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "c": "not a float"}

        # Act
        result = validator.validate(config)

        # Assert
        self.assertFalse(result.valid)
        # Should have 2 missing field errors (a, b) and 1 type error (c)
        self.assertEqual(len(result.errors), 3)


class ValidationResultTests(TestCase):
    def test_ValidationResult__ValidTrue__EmptyErrors(self):
        # Arrange & Act
        result = ValidationResult(valid=True)

        # Assert
        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])

    def test_ValidationResult__ValidFalse__WithErrors(self):
        # Arrange
        error = MissingFieldError("field", "target")

        # Act
        result = ValidationResult(valid=False, errors=[error])

        # Assert
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)


class ConfigValidatorEdgeCaseTests(TestCase):
    """Tests for edge cases and uncovered code paths."""

    def _empty_store(self) -> ConfigStore:
        store = ConfigStore()
        store._known_references.clear()
        return store

    def test_validate__ClassWithVarKeyword__SkipsKwargsValidation(self):
        # Arrange
        store = self._empty_store()

        class ModelWithKwargs:
            def __init__(self, required: int, **kwargs: str) -> None:
                self.required = required
                self.kwargs = kwargs

        store.register("model", ModelWithKwargs)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "required": 42, "extra": "value"}

        # Act
        result = validator.validate(config)

        # Assert - should be valid, **kwargs should be skipped
        self.assertTrue(result.valid)

    def test_validate__ClassWithVarPositional__SkipsArgsValidation(self):
        # Arrange
        store = self._empty_store()

        class ModelWithArgs:
            def __init__(self, required: int, *args: int) -> None:
                self.required = required
                self.args = args

        store.register("model", ModelWithArgs)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "required": 42}

        # Act
        result = validator.validate(config)

        # Assert - should be valid, *args should be skipped
        self.assertTrue(result.valid)

    def test_validate__TypeHintsFails__SkipsTypeValidation(self):
        # Arrange
        store = self._empty_store()

        class ModelWithBadHints:
            def __init__(self, value: "NonExistentType") -> None:  # noqa: F821
                self.value = value

        store.register("model", ModelWithBadHints)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "value": 42}

        # Act - should not raise, just skip type validation
        # Mock get_type_hints to raise an exception
        with patch(
            "rconfig.ConfigValidator.get_type_hints",
            side_effect=NameError("name 'NonExistentType' is not defined"),
        ):
            result = validator.validate(config)

        # Assert - valid because type hints couldn't be resolved
        self.assertTrue(result.valid)

    def test_validate__UnionType__ValidatesAllOptions(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            value: Union[int, str]

        store.register("model", Model)
        validator = ConfigValidator(store)

        # Act & Assert - int is valid
        config = {"_target_": "model", "value": 42}
        result = validator.validate(config)
        self.assertTrue(result.valid)

        # Act & Assert - str is valid
        config = {"_target_": "model", "value": "hello"}
        result = validator.validate(config)
        self.assertTrue(result.valid)

        # Act & Assert - list is invalid
        config = {"_target_": "model", "value": [1, 2, 3]}
        result = validator.validate(config)
        self.assertFalse(result.valid)

    def test_validate__UntypedList__AcceptsAnyList(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            items: list  # No element type specified

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "items": [1, "mixed", 3.14]}

        # Act
        result = validator.validate(config)

        # Assert - any list should be valid
        self.assertTrue(result.valid)

    def test_validate__UntypedDict__AcceptsAnyDict(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            params: dict  # No key/value types specified

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "params": {1: "one", "two": 2}}

        # Act
        result = validator.validate(config)

        # Assert - any dict should be valid
        self.assertTrue(result.valid)

    def test_validate__NonListForListField__ReturnsTypeMismatchError(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            layers: list[int]

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "layers": "not a list"}

        # Act
        result = validator.validate(config)

        # Assert
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIsInstance(result.errors[0], TypeMismatchError)

    def test_validate__NonDictForDictField__ReturnsTypeMismatchError(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            params: dict[str, int]

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "params": "not a dict"}

        # Act
        result = validator.validate(config)

        # Assert
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertIsInstance(result.errors[0], TypeMismatchError)

    def test_validate__NestedConfigForIntField__ValidatesRecursively(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Inner:
            value: int

        @dataclass
        class Outer:
            data: int  # Expects int, but we'll pass nested config

        store.register("inner", Inner)
        store.register("outer", Outer)
        validator = ConfigValidator(store)
        config = {
            "_target_": "outer",
            "data": {"_target_": "inner", "value": 42},  # Nested config where int expected
        }

        # Act
        result = validator.validate(config)

        # Assert - nested config is validated recursively (returns True in _type_matches)
        self.assertTrue(result.valid)

    def test_validate__TupleType__ReturnsTypeMismatchError(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            coords: tuple[int, int]

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "coords": (1, 2)}

        # Act
        result = validator.validate(config)

        # Assert - tuple is not handled, falls through to return False
        self.assertFalse(result.valid)
        self.assertIsInstance(result.errors[0], TypeMismatchError)

    def test_validate__UnionTypeInError__FormatsTypeReprCorrectly(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            value: Union[int, str]

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "value": 3.14}  # float is not int|str

        # Act
        result = validator.validate(config)

        # Assert
        self.assertFalse(result.valid)
        error = result.errors[0]
        self.assertIsInstance(error, TypeMismatchError)
        # Check the expected type repr contains both types
        self.assertIn("int", error.expected)
        self.assertIn("str", error.expected)

    def test_validate__OptionalInError__FormatsTypeReprCorrectly(self):
        # Arrange
        store = self._empty_store()

        @dataclass
        class Model:
            value: Optional[int]

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "value": "not an int"}

        # Act
        result = validator.validate(config)

        # Assert
        self.assertFalse(result.valid)
        error = result.errors[0]
        self.assertIsInstance(error, TypeMismatchError)
        # Optional[int] should be formatted as "int | None"
        self.assertIn("int", error.expected)
        self.assertIn("None", error.expected)

    def test_validate__NoneTypeField__AcceptsNone(self):
        # Arrange - Test field typed as exactly None (rare edge case)
        store = self._empty_store()

        @dataclass
        class Model:
            sentinel: None  # Field that only accepts None

        store.register("model", Model)
        validator = ConfigValidator(store)

        # Act & Assert - None is valid
        config = {"_target_": "model", "sentinel": None}
        result = validator.validate(config)
        self.assertTrue(result.valid)

        # Act & Assert - non-None is invalid
        config = {"_target_": "model", "sentinel": 42}
        result = validator.validate(config)
        self.assertFalse(result.valid)

    def test_validate__UntypedListInError__FormatsTypeReprCorrectly(self):
        # Arrange - tests _type_repr for untyped list (line 247)
        store = self._empty_store()

        @dataclass
        class Model:
            items: list  # Untyped list

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "items": "not a list"}

        # Act
        result = validator.validate(config)

        # Assert
        self.assertFalse(result.valid)
        error = result.errors[0]
        self.assertIsInstance(error, TypeMismatchError)
        self.assertEqual(error.expected, "list")

    def test_validate__UntypedDictInError__FormatsTypeReprCorrectly(self):
        # Arrange - tests _type_repr for untyped dict (line 252)
        store = self._empty_store()

        @dataclass
        class Model:
            params: dict  # Untyped dict

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "params": "not a dict"}

        # Act
        result = validator.validate(config)

        # Assert
        self.assertFalse(result.valid)
        error = result.errors[0]
        self.assertIsInstance(error, TypeMismatchError)
        self.assertEqual(error.expected, "dict")

    def test_validate__ComplexTypeWithoutName__FormatsTypeReprAsFallback(self):
        # Arrange - test _type_repr fallback for type without __name__ (line 257)
        store = self._empty_store()

        # Use a generic alias that doesn't have __name__
        from typing import Callable

        @dataclass
        class Model:
            callback: Callable[[int], str]  # Callable doesn't have simple __name__

        store.register("model", Model)
        validator = ConfigValidator(store)
        config = {"_target_": "model", "callback": "not callable"}

        # Act
        result = validator.validate(config)

        # Assert - should fail with some type repr (fallback to str())
        self.assertFalse(result.valid)
        error = result.errors[0]
        self.assertIsInstance(error, TypeMismatchError)
        # The expected should be some string representation
        self.assertTrue(len(error.expected) > 0)
