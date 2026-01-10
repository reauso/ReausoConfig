"""Unit tests for DeprecationInfo."""

from unittest import TestCase

from rconfig.deprecation.info import DeprecationInfo


class DeprecationInfoTests(TestCase):
    """Tests for the DeprecationInfo dataclass."""

    def test_init__MinimalFields__CreatesInfo(self):
        # Act
        info = DeprecationInfo(pattern="old_key")

        # Assert
        self.assertEqual(info.pattern, "old_key")
        self.assertIsNone(info.matched_path)
        self.assertIsNone(info.new_key)
        self.assertIsNone(info.message)
        self.assertIsNone(info.remove_in)
        self.assertIsNone(info.policy)

    def test_init__AllFields__CreatesInfoWithAllFields(self):
        # Act
        info = DeprecationInfo(
            pattern="old_key",
            matched_path="model.old_key",
            new_key="new_key",
            message="Custom message",
            remove_in="2.0.0",
            policy="error",
        )

        # Assert
        self.assertEqual(info.pattern, "old_key")
        self.assertEqual(info.matched_path, "model.old_key")
        self.assertEqual(info.new_key, "new_key")
        self.assertEqual(info.message, "Custom message")
        self.assertEqual(info.remove_in, "2.0.0")
        self.assertEqual(info.policy, "error")

    def test_frozen__Immutable__CannotModify(self):
        # Arrange
        info = DeprecationInfo(pattern="old_key")

        # Act & Assert
        with self.assertRaises(Exception):  # FrozenInstanceError
            info.pattern = "modified"  # type: ignore

    def test_withMatchedPath__CreatesNewCopy__PreservesFields(self):
        # Arrange
        info = DeprecationInfo(
            pattern="**.lr",
            new_key="optimizer.lr",
            message="Use optimizer.lr",
            remove_in="3.0.0",
            policy="warn",
        )

        # Act
        matched = info.with_matched_path("model.encoder.lr")

        # Assert
        self.assertEqual(matched.pattern, "**.lr")
        self.assertEqual(matched.matched_path, "model.encoder.lr")
        self.assertEqual(matched.new_key, "optimizer.lr")
        self.assertEqual(matched.message, "Use optimizer.lr")
        self.assertEqual(matched.remove_in, "3.0.0")
        self.assertEqual(matched.policy, "warn")

    def test_withMatchedPath__DoesNotModifyOriginal__OriginalUnchanged(self):
        # Arrange
        info = DeprecationInfo(pattern="**.lr")

        # Act
        _ = info.with_matched_path("model.lr")

        # Assert
        self.assertIsNone(info.matched_path)

    def test_toDict__MinimalFields__ReturnsMinimalDict(self):
        # Arrange
        info = DeprecationInfo(pattern="old_key")

        # Act
        result = info.to_dict()

        # Assert
        self.assertEqual(result, {"pattern": "old_key"})

    def test_toDict__AllFields__ReturnsFullDict(self):
        # Arrange
        info = DeprecationInfo(
            pattern="old_key",
            matched_path="model.old_key",
            new_key="new_key",
            message="Custom message",
            remove_in="2.0.0",
            policy="error",
        )

        # Act
        result = info.to_dict()

        # Assert
        self.assertEqual(result, {
            "pattern": "old_key",
            "matched_path": "model.old_key",
            "new_key": "new_key",
            "message": "Custom message",
            "remove_in": "2.0.0",
            "policy": "error",
        })

    def test_toDict__PartialFields__OmitsNoneValues(self):
        # Arrange
        info = DeprecationInfo(
            pattern="old_key",
            new_key="new_key",
            # No message, remove_in, or policy
        )

        # Act
        result = info.to_dict()

        # Assert
        self.assertEqual(result, {
            "pattern": "old_key",
            "new_key": "new_key",
        })
        self.assertNotIn("message", result)
        self.assertNotIn("remove_in", result)
        self.assertNotIn("policy", result)

    def test_equality__SameFields__Equal(self):
        # Arrange
        info1 = DeprecationInfo(pattern="key", new_key="new")
        info2 = DeprecationInfo(pattern="key", new_key="new")

        # Assert
        self.assertEqual(info1, info2)

    def test_equality__DifferentFields__NotEqual(self):
        # Arrange
        info1 = DeprecationInfo(pattern="key1")
        info2 = DeprecationInfo(pattern="key2")

        # Assert
        self.assertNotEqual(info1, info2)

    def test_hash__Frozen__CanBeUsedAsKey(self):
        # Arrange
        info = DeprecationInfo(pattern="key")

        # Act
        d = {info: "value"}

        # Assert
        self.assertEqual(d[info], "value")
