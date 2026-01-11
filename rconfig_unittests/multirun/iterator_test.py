"""Unit tests for MultirunIterator."""

from types import MappingProxyType
from unittest import TestCase

from rconfig.multirun import MultirunIterator, MultirunResult


def _make_result(overrides: dict) -> MultirunResult[str]:
    """Helper to create a MultirunResult for testing."""
    return MultirunResult(
        config=MappingProxyType(overrides),
        overrides=MappingProxyType(overrides),
        _instance=f"instance_{overrides}",
        _error=None,
    )


class MultirunIteratorTests(TestCase):
    """Tests for the MultirunIterator class."""

    def test_MultirunIterator__Len__ReturnsRunCount(self):
        # Arrange
        configs = [{"a": 1}, {"a": 2}, {"a": 3}]
        iterator = MultirunIterator(configs, _make_result)

        # Act
        length = len(iterator)

        # Assert
        self.assertEqual(length, 3)

    def test_MultirunIterator__Iter__ReturnsNewIterator(self):
        # Arrange
        configs = [{"a": 1}, {"a": 2}]
        iterator = MultirunIterator(configs, _make_result)

        # Act
        new_iter = iter(iterator)

        # Assert
        self.assertIsInstance(new_iter, MultirunIterator)
        self.assertIsNot(new_iter, iterator)

    def test_MultirunIterator__Next__YieldsResults(self):
        # Arrange
        configs = [{"a": 1}, {"a": 2}]
        iterator = MultirunIterator(configs, _make_result)

        # Act
        results = list(iterator)

        # Assert
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], MultirunResult)
        self.assertIsInstance(results[1], MultirunResult)

    def test_MultirunIterator__Next__RaisesStopIteration(self):
        # Arrange
        configs = [{"a": 1}]
        iterator = MultirunIterator(configs, _make_result)

        # Act
        next(iterator)  # First item

        # Assert
        with self.assertRaises(StopIteration):
            next(iterator)

    def test_MultirunIterator__Reversed__ReturnsReversedIterator(self):
        # Arrange
        configs = [{"a": 1}, {"a": 2}, {"a": 3}]
        iterator = MultirunIterator(configs, _make_result)

        # Act
        reversed_iter = reversed(iterator)
        results = list(reversed_iter)

        # Assert
        self.assertEqual(len(results), 3)
        self.assertEqual(dict(results[0].overrides), {"a": 3})
        self.assertEqual(dict(results[1].overrides), {"a": 2})
        self.assertEqual(dict(results[2].overrides), {"a": 1})

    def test_MultirunIterator__GetItemInt__ReturnsSingleResult(self):
        # Arrange
        configs = [{"a": 1}, {"a": 2}, {"a": 3}]
        iterator = MultirunIterator(configs, _make_result)

        # Act
        result = iterator[1]

        # Assert
        self.assertIsInstance(result, MultirunResult)
        self.assertEqual(dict(result.overrides), {"a": 2})

    def test_MultirunIterator__GetItemInt__NegativeIndex__WorksFromEnd(self):
        # Arrange
        configs = [{"a": 1}, {"a": 2}, {"a": 3}]
        iterator = MultirunIterator(configs, _make_result)

        # Act
        result = iterator[-1]

        # Assert
        self.assertEqual(dict(result.overrides), {"a": 3})

    def test_MultirunIterator__GetItemInt__OutOfRange__RaisesIndexError(self):
        # Arrange
        configs = [{"a": 1}, {"a": 2}]
        iterator = MultirunIterator(configs, _make_result)

        # Act & Assert
        with self.assertRaises(IndexError) as ctx:
            _ = iterator[5]

        self.assertIn("out of range", str(ctx.exception))

    def test_MultirunIterator__GetItemSlice__ReturnsNewIterator(self):
        # Arrange
        configs = [{"a": 1}, {"a": 2}, {"a": 3}, {"a": 4}]
        iterator = MultirunIterator(configs, _make_result)

        # Act
        sliced = iterator[1:3]

        # Assert
        self.assertIsInstance(sliced, MultirunIterator)
        self.assertEqual(len(sliced), 2)
        results = list(sliced)
        self.assertEqual(dict(results[0].overrides), {"a": 2})
        self.assertEqual(dict(results[1].overrides), {"a": 3})

    def test_MultirunIterator__GetItemSlice__LazyInstantiation(self):
        # Arrange
        call_count = 0

        def counting_make_result(overrides: dict) -> MultirunResult[str]:
            nonlocal call_count
            call_count += 1
            return _make_result(overrides)

        configs = [{"a": i} for i in range(10)]
        iterator = MultirunIterator(configs, counting_make_result)

        # Act
        sliced = iterator[5:7]  # Should not instantiate yet

        # Assert - no instantiation happened yet
        self.assertEqual(call_count, 0)

        # Act - iterate
        list(sliced)

        # Assert - only 2 items instantiated
        self.assertEqual(call_count, 2)

    def test_MultirunIterator__GetItemInvalidType__RaisesTypeError(self):
        # Arrange
        configs = [{"a": 1}]
        iterator = MultirunIterator(configs, _make_result)

        # Act & Assert
        with self.assertRaises(TypeError) as ctx:
            _ = iterator["invalid"]  # type: ignore

        self.assertIn("str", str(ctx.exception))

    def test_MultirunIterator__EmptyConfigs__LenIsZero(self):
        # Arrange
        iterator = MultirunIterator([], _make_result)

        # Act & Assert
        self.assertEqual(len(iterator), 0)
        self.assertEqual(list(iterator), [])

    def test_MultirunIterator__MultipleIterations__EachStartsFresh(self):
        # Arrange
        configs = [{"a": 1}, {"a": 2}]
        iterator = MultirunIterator(configs, _make_result)

        # Act
        first_pass = list(iterator)
        second_pass = list(iter(iterator))

        # Assert
        self.assertEqual(len(first_pass), 2)
        self.assertEqual(len(second_pass), 2)
