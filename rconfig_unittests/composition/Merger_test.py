from unittest import TestCase

from rconfig.composition import deep_merge
from rconfig.errors import MergeError


class DeepMergeTests(TestCase):
    """Tests for the deep_merge function."""

    def test_deep_merge__NestedDictMerge__RecursiveMergeLeafOverrides(self):
        # Arrange
        base = {
            "a": 1,
            "b": {
                "c": 2,
                "d": 3,
                "nested": {
                    "x": 10,
                    "y": 20,
                },
            },
        }
        override = {
            "b": {
                "c": 100,
                "nested": {
                    "x": 999,
                },
            },
        }

        # Act
        result = deep_merge(base, override)

        # Assert
        self.assertEqual(
            result,
            {
                "a": 1,
                "b": {
                    "c": 100,  # Overridden
                    "d": 3,  # Preserved
                    "nested": {
                        "x": 999,  # Overridden
                        "y": 20,  # Preserved
                    },
                },
            },
        )

    def test_deep_merge__ListReplacement__LaterListReplacesEarlier(self):
        # Arrange
        base = {"callbacks": ["logger", "checkpoint"], "other": "value"}
        override = {"callbacks": ["early_stop"]}

        # Act
        result = deep_merge(base, override)

        # Assert
        self.assertEqual(result["callbacks"], ["early_stop"])
        self.assertEqual(result["other"], "value")

    def test_deep_merge__OverrideSingleNestedKey__OtherKeysPreserved(self):
        # Arrange
        base = {
            "optimizer": {
                "type": "adam",
                "lr": 0.001,
                "betas": [0.9, 0.999],
            }
        }
        override = {"optimizer": {"lr": 0.01}}

        # Act
        result = deep_merge(base, override)

        # Assert
        self.assertEqual(result["optimizer"]["type"], "adam")  # Preserved
        self.assertEqual(result["optimizer"]["lr"], 0.01)  # Overridden
        self.assertEqual(result["optimizer"]["betas"], [0.9, 0.999])  # Preserved

    def test_deep_merge__MultipleLevelsOfNesting__AllLevelsMergedCorrectly(self):
        # Arrange
        base = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "a": 1,
                            "b": 2,
                        },
                        "other": "value",
                    },
                },
            },
        }
        override = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "a": 999,
                        },
                    },
                },
            },
        }

        # Act
        result = deep_merge(base, override)

        # Assert
        self.assertEqual(result["level1"]["level2"]["level3"]["level4"]["a"], 999)
        self.assertEqual(result["level1"]["level2"]["level3"]["level4"]["b"], 2)
        self.assertEqual(result["level1"]["level2"]["level3"]["other"], "value")

    def test_deep_merge__NewKeysInOverride__AddedToResult(self):
        # Arrange
        base = {"a": 1}
        override = {"b": 2, "c": {"d": 3}}

        # Act
        result = deep_merge(base, override)

        # Assert
        self.assertEqual(result, {"a": 1, "b": 2, "c": {"d": 3}})

    def test_deep_merge__EmptyBase__ReturnsOverride(self):
        # Arrange
        base = {}
        override = {"a": 1, "b": {"c": 2}}

        # Act
        result = deep_merge(base, override)

        # Assert
        self.assertEqual(result, {"a": 1, "b": {"c": 2}})

    def test_deep_merge__EmptyOverride__ReturnsBase(self):
        # Arrange
        base = {"a": 1, "b": {"c": 2}}
        override = {}

        # Act
        result = deep_merge(base, override)

        # Assert
        self.assertEqual(result, {"a": 1, "b": {"c": 2}})

    def test_deep_merge__ScalarToDict__OverrideWins(self):
        # Arrange - base has scalar, override has dict
        base = {"value": 42}
        override = {"value": {"nested": "dict"}}

        # Act
        result = deep_merge(base, override)

        # Assert
        self.assertEqual(result["value"], {"nested": "dict"})

    def test_deep_merge__DictToScalar__OverrideWins(self):
        # Arrange - base has dict, override has scalar
        base = {"value": {"nested": "dict"}}
        override = {"value": 42}

        # Act
        result = deep_merge(base, override)

        # Assert
        self.assertEqual(result["value"], 42)

    def test_deep_merge__DoesNotMutateInputs__ReturnsFreshDict(self):
        # Arrange
        base = {"a": 1, "b": {"c": 2}}
        override = {"b": {"c": 10, "d": 20}}
        original_base = {"a": 1, "b": {"c": 2}}
        original_override = {"b": {"c": 10, "d": 20}}

        # Act
        result = deep_merge(base, override)

        # Assert - inputs unchanged
        self.assertEqual(base, original_base)
        self.assertEqual(override, original_override)
        # Result is different object
        self.assertIsNot(result, base)
        self.assertIsNot(result, override)


class ExtendTests(TestCase):
    """Tests for the _extend_ list operation."""

    def test_extend__AppendsToList__ItemsAddedAtEnd(self):
        # Arrange
        base = {"callbacks": ["logger", "checkpoint"]}
        override = {"callbacks": {"_extend_": ["early_stop", "profiler"]}}

        # Act
        result = deep_merge(base, override)

        # Assert
        self.assertEqual(
            result["callbacks"], ["logger", "checkpoint", "early_stop", "profiler"]
        )

    def test_extend__OnNonListTarget__RaisesMergeError(self):
        # Arrange
        base = {"value": "not a list"}
        override = {"value": {"_extend_": ["item"]}}

        # Act & Assert
        with self.assertRaises(MergeError) as ctx:
            deep_merge(base, override)

        self.assertIn("_extend_", str(ctx.exception))
        self.assertIn("non-list", str(ctx.exception))
        self.assertIn("str", str(ctx.exception))

    def test_extend__WithNonListValue__RaisesMergeError(self):
        # Arrange
        base = {"items": ["a", "b"]}
        override = {"items": {"_extend_": "not a list"}}

        # Act & Assert
        with self.assertRaises(MergeError) as ctx:
            deep_merge(base, override)

        self.assertIn("_extend_", str(ctx.exception))
        self.assertIn("must be a list", str(ctx.exception))

    def test_extend__WithEmptyList__ReturnsOriginalList(self):
        # Arrange
        base = {"items": ["a", "b"]}
        override = {"items": {"_extend_": []}}

        # Act
        result = deep_merge(base, override)

        # Assert
        self.assertEqual(result["items"], ["a", "b"])

    def test_extend__WithOtherKeys__RaisesMergeError(self):
        # Arrange
        base = {"items": ["a", "b"]}
        override = {"items": {"_extend_": ["c"], "extra": "key"}}

        # Act & Assert
        with self.assertRaises(MergeError) as ctx:
            deep_merge(base, override)

        self.assertIn("_extend_", str(ctx.exception))
        self.assertIn("cannot be combined", str(ctx.exception))


class PrependTests(TestCase):
    """Tests for the _prepend_ list operation."""

    def test_prepend__PrependsToList__ItemsAddedAtStart(self):
        # Arrange
        base = {"callbacks": ["logger", "checkpoint"]}
        override = {"callbacks": {"_prepend_": ["early_stop", "profiler"]}}

        # Act
        result = deep_merge(base, override)

        # Assert
        self.assertEqual(
            result["callbacks"], ["early_stop", "profiler", "logger", "checkpoint"]
        )

    def test_prepend__OnNonListTarget__RaisesMergeError(self):
        # Arrange
        base = {"value": 42}
        override = {"value": {"_prepend_": ["item"]}}

        # Act & Assert
        with self.assertRaises(MergeError) as ctx:
            deep_merge(base, override)

        self.assertIn("_prepend_", str(ctx.exception))
        self.assertIn("non-list", str(ctx.exception))

    def test_prepend__WithNonListValue__RaisesMergeError(self):
        # Arrange
        base = {"items": ["a", "b"]}
        override = {"items": {"_prepend_": {"not": "a list"}}}

        # Act & Assert
        with self.assertRaises(MergeError) as ctx:
            deep_merge(base, override)

        self.assertIn("_prepend_", str(ctx.exception))
        self.assertIn("must be a list", str(ctx.exception))

    def test_prepend__WithEmptyList__ReturnsOriginalList(self):
        # Arrange
        base = {"items": ["a", "b"]}
        override = {"items": {"_prepend_": []}}

        # Act
        result = deep_merge(base, override)

        # Assert
        self.assertEqual(result["items"], ["a", "b"])


class CombinedListOperationsTests(TestCase):
    """Tests for combining _extend_ and _prepend_."""

    def test_extend_and_prepend__SameBlock__RaisesMergeError(self):
        # Arrange
        base = {"items": ["a", "b"]}
        override = {"items": {"_extend_": ["c"], "_prepend_": ["z"]}}

        # Act & Assert
        with self.assertRaises(MergeError) as ctx:
            deep_merge(base, override)

        self.assertIn("Cannot use both", str(ctx.exception))
        self.assertIn("_extend_", str(ctx.exception))
        self.assertIn("_prepend_", str(ctx.exception))


class DeepMergePathTrackingTests(TestCase):
    """Tests for path tracking in deep_merge errors."""

    def test_deep_merge__ErrorIncludesPath__ShowsFullPath(self):
        # Arrange
        base = {"level1": {"level2": {"value": "not a list"}}}
        override = {"level1": {"level2": {"value": {"_extend_": ["item"]}}}}

        # Act & Assert
        with self.assertRaises(MergeError) as ctx:
            deep_merge(base, override)

        self.assertIn("level1.level2.value", str(ctx.exception))
