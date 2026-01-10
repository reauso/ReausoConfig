"""Tests for PositionMap and Position classes."""

from dataclasses import FrozenInstanceError
from unittest import TestCase

from rconfig.loaders.position_map import Position, PositionMap


class PositionTests(TestCase):
    """Tests for Position dataclass."""

    def test_Position__Creation__StoresLineAndColumn(self):
        # Act
        pos = Position(line=5, column=10)

        # Assert
        self.assertEqual(pos.line, 5)
        self.assertEqual(pos.column, 10)

    def test_Position__Frozen__CannotModify(self):
        # Arrange
        pos = Position(line=1, column=1)

        # Act & Assert
        with self.assertRaises(FrozenInstanceError):
            pos.line = 2  # type: ignore[misc]

    def test_Position__Equality__ComparesCorrectly(self):
        # Arrange
        pos1 = Position(line=5, column=10)
        pos2 = Position(line=5, column=10)
        pos3 = Position(line=5, column=11)

        # Assert
        self.assertEqual(pos1, pos2)
        self.assertNotEqual(pos1, pos3)

    def test_Position__Hash__CanBeUsedInSet(self):
        # Arrange
        pos1 = Position(line=5, column=10)
        pos2 = Position(line=5, column=10)

        # Act
        positions = {pos1, pos2}

        # Assert
        self.assertEqual(len(positions), 1)


class PositionMapTests(TestCase):
    """Tests for PositionMap class."""

    def test_PositionMap__EmptyInit__CreatesEmptyMap(self):
        # Act
        pmap = PositionMap()

        # Assert
        self.assertEqual(len(pmap), 0)
        self.assertEqual(dict(pmap), {})

    def test_PositionMap__InitWithData__StoresData(self):
        # Act
        pmap = PositionMap({"key": "value", "number": 42})

        # Assert
        self.assertEqual(pmap["key"], "value")
        self.assertEqual(pmap["number"], 42)

    def test_PositionMap__SetAndGetPosition__ReturnsCorrectPosition(self):
        # Arrange
        pmap = PositionMap({"key": "value"})

        # Act
        pmap.set_position("key", line=5, column=10)
        pos = pmap.get_position("key")

        # Assert
        self.assertIsNotNone(pos)
        self.assertEqual(pos.line, 5)
        self.assertEqual(pos.column, 10)

    def test_PositionMap__GetLine__ReturnsLineOnly(self):
        # Arrange
        pmap = PositionMap({"key": "value"})
        pmap.set_position("key", line=5, column=10)

        # Act
        line = pmap.get_line("key")

        # Assert
        self.assertEqual(line, 5)

    def test_PositionMap__GetColumn__ReturnsColumnOnly(self):
        # Arrange
        pmap = PositionMap({"key": "value"})
        pmap.set_position("key", line=5, column=10)

        # Act
        column = pmap.get_column("key")

        # Assert
        self.assertEqual(column, 10)

    def test_PositionMap__NonexistentKey__ReturnsNone(self):
        # Arrange
        pmap = PositionMap({"key": "value"})

        # Act & Assert
        self.assertIsNone(pmap.get_position("nonexistent"))
        self.assertIsNone(pmap.get_line("nonexistent"))
        self.assertIsNone(pmap.get_column("nonexistent"))

    def test_PositionMap__HasPosition__ReturnsTrueForExistingKey(self):
        # Arrange
        pmap = PositionMap({"key": "value"})
        pmap.set_position("key", line=1, column=1)

        # Act & Assert
        self.assertTrue(pmap.has_position("key"))
        self.assertFalse(pmap.has_position("nonexistent"))

    def test_PositionMap__DictBehavior__WorksAsDict(self):
        # Arrange
        pmap = PositionMap({"a": 1, "b": 2})

        # Act & Assert - dict operations
        self.assertIn("a", pmap)
        self.assertEqual(list(pmap.keys()), ["a", "b"])
        self.assertEqual(list(pmap.values()), [1, 2])
        self.assertEqual(len(pmap), 2)

        # Modify
        pmap["c"] = 3
        self.assertEqual(pmap["c"], 3)

        # Delete
        del pmap["b"]
        self.assertNotIn("b", pmap)

    def test_PositionMap__UpdatePosition__OverwritesPrevious(self):
        # Arrange
        pmap = PositionMap({"key": "value"})
        pmap.set_position("key", line=1, column=1)

        # Act
        pmap.set_position("key", line=5, column=10)

        # Assert
        pos = pmap.get_position("key")
        self.assertEqual(pos.line, 5)
        self.assertEqual(pos.column, 10)

    def test_PositionMap__EmptyMap__NoPositions(self):
        # Arrange
        pmap = PositionMap()

        # Act & Assert
        self.assertIsNone(pmap.get_position("any"))
        self.assertFalse(pmap.has_position("any"))

    def test_PositionMap__MultipleKeys__TracksEachSeparately(self):
        # Arrange
        pmap = PositionMap({"a": 1, "b": 2, "c": 3})

        # Act
        pmap.set_position("a", line=1, column=1)
        pmap.set_position("b", line=5, column=10)
        pmap.set_position("c", line=10, column=20)

        # Assert
        self.assertEqual(pmap.get_line("a"), 1)
        self.assertEqual(pmap.get_line("b"), 5)
        self.assertEqual(pmap.get_line("c"), 10)
        self.assertEqual(pmap.get_column("a"), 1)
        self.assertEqual(pmap.get_column("b"), 10)
        self.assertEqual(pmap.get_column("c"), 20)
