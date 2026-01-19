"""Unit tests for Diff core data structures."""

from __future__ import annotations

import pytest

from rconfig.diff import ConfigDiff, DiffEntry, DiffEntryType


class TestDiffEntryType:
    """Tests for DiffEntryType enum."""

    def test_enum_values(self) -> None:
        """DiffEntryType has expected string values."""
        assert DiffEntryType.ADDED == "added"
        assert DiffEntryType.REMOVED == "removed"
        assert DiffEntryType.CHANGED == "changed"
        assert DiffEntryType.UNCHANGED == "unchanged"

    def test_enum_is_str(self) -> None:
        """DiffEntryType values are strings."""
        assert isinstance(DiffEntryType.ADDED, str)
        assert isinstance(DiffEntryType.REMOVED, str)


class TestDiffEntry:
    """Tests for DiffEntry frozen dataclass."""

    def test_create_added_entry(self) -> None:
        """Can create an added entry."""
        entry = DiffEntry(
            path="model.dropout",
            diff_type=DiffEntryType.ADDED,
            right_value=0.1,
        )
        assert entry.path == "model.dropout"
        assert entry.diff_type == DiffEntryType.ADDED
        assert entry.left_value is None
        assert entry.right_value == 0.1

    def test_create_removed_entry(self) -> None:
        """Can create a removed entry."""
        entry = DiffEntry(
            path="legacy.param",
            diff_type=DiffEntryType.REMOVED,
            left_value="old",
        )
        assert entry.path == "legacy.param"
        assert entry.diff_type == DiffEntryType.REMOVED
        assert entry.left_value == "old"
        assert entry.right_value is None

    def test_create_changed_entry(self) -> None:
        """Can create a changed entry."""
        entry = DiffEntry(
            path="model.lr",
            diff_type=DiffEntryType.CHANGED,
            left_value=0.001,
            right_value=0.01,
        )
        assert entry.path == "model.lr"
        assert entry.diff_type == DiffEntryType.CHANGED
        assert entry.left_value == 0.001
        assert entry.right_value == 0.01

    def test_create_unchanged_entry(self) -> None:
        """Can create an unchanged entry."""
        entry = DiffEntry(
            path="model.layers",
            diff_type=DiffEntryType.UNCHANGED,
            left_value=4,
            right_value=4,
        )
        assert entry.path == "model.layers"
        assert entry.diff_type == DiffEntryType.UNCHANGED
        assert entry.left_value == 4
        assert entry.right_value == 4

    def test_entry_is_frozen(self) -> None:
        """DiffEntry is immutable."""
        entry = DiffEntry(
            path="test",
            diff_type=DiffEntryType.ADDED,
            right_value=1,
        )
        with pytest.raises(AttributeError):
            entry.path = "changed"  # type: ignore

    def test_entry_with_provenance(self) -> None:
        """DiffEntry can store provenance info."""
        # Create a mock provenance entry (just testing the field exists)
        entry = DiffEntry(
            path="model.lr",
            diff_type=DiffEntryType.CHANGED,
            left_value=0.001,
            right_value=0.01,
            left_provenance=None,
            right_provenance=None,
        )
        assert entry.left_provenance is None
        assert entry.right_provenance is None


class TestConfigDiff:
    """Tests for ConfigDiff mapping class."""

    def test_empty_diff(self) -> None:
        """Empty ConfigDiff has no entries."""
        diff = ConfigDiff({})
        assert len(diff) == 0
        assert diff.is_empty()

    def test_getitem(self) -> None:
        """Can access entries by path."""
        entry = DiffEntry("model.lr", DiffEntryType.CHANGED, 0.001, 0.01)
        diff = ConfigDiff({"model.lr": entry})
        assert diff["model.lr"] == entry

    def test_getitem_missing(self) -> None:
        """KeyError for missing paths."""
        diff = ConfigDiff({})
        with pytest.raises(KeyError):
            _ = diff["missing"]

    def test_contains(self) -> None:
        """Can check path membership."""
        entry = DiffEntry("model.lr", DiffEntryType.CHANGED, 0.001, 0.01)
        diff = ConfigDiff({"model.lr": entry})
        assert "model.lr" in diff
        assert "missing" not in diff

    def test_len(self) -> None:
        """Length reflects entry count."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
        }
        diff = ConfigDiff(entries)
        assert len(diff) == 2

    def test_iter(self) -> None:
        """Can iterate over paths."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
        }
        diff = ConfigDiff(entries)
        paths = list(diff)
        assert "a" in paths
        assert "b" in paths

    def test_keys_values_items(self) -> None:
        """Mapping methods work correctly."""
        entry_a = DiffEntry("a", DiffEntryType.ADDED, right_value=1)
        entry_b = DiffEntry("b", DiffEntryType.REMOVED, left_value=2)
        diff = ConfigDiff({"a": entry_a, "b": entry_b})

        assert set(diff.keys()) == {"a", "b"}
        assert set(diff.values()) == {entry_a, entry_b}
        assert set(diff.items()) == {("a", entry_a), ("b", entry_b)}

    def test_get_with_default(self) -> None:
        """get() returns default for missing paths."""
        diff = ConfigDiff({})
        assert diff.get("missing") is None
        assert diff.get("missing", "default") == "default"

    def test_added_property(self) -> None:
        """added property returns only added entries."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
            "c": DiffEntry("c", DiffEntryType.CHANGED, 1, 2),
        }
        diff = ConfigDiff(entries)
        assert len(diff.added) == 1
        assert "a" in diff.added

    def test_removed_property(self) -> None:
        """removed property returns only removed entries."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
            "c": DiffEntry("c", DiffEntryType.CHANGED, 1, 2),
        }
        diff = ConfigDiff(entries)
        assert len(diff.removed) == 1
        assert "b" in diff.removed

    def test_changed_property(self) -> None:
        """changed property returns only changed entries."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
            "c": DiffEntry("c", DiffEntryType.CHANGED, 1, 2),
        }
        diff = ConfigDiff(entries)
        assert len(diff.changed) == 1
        assert "c" in diff.changed

    def test_unchanged_property(self) -> None:
        """unchanged property returns only unchanged entries."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "d": DiffEntry("d", DiffEntryType.UNCHANGED, 3, 3),
        }
        diff = ConfigDiff(entries)
        assert len(diff.unchanged) == 1
        assert "d" in diff.unchanged

    def test_is_empty_with_unchanged_only(self) -> None:
        """is_empty() returns True when only unchanged entries exist."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.UNCHANGED, 1, 1),
            "b": DiffEntry("b", DiffEntryType.UNCHANGED, 2, 2),
        }
        diff = ConfigDiff(entries)
        assert diff.is_empty()

    def test_is_empty_with_changes(self) -> None:
        """is_empty() returns False when there are changes."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.UNCHANGED, 1, 1),
            "b": DiffEntry("b", DiffEntryType.ADDED, right_value=2),
        }
        diff = ConfigDiff(entries)
        assert not diff.is_empty()

    def test_to_dict(self) -> None:
        """to_dict() returns plain dictionary."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.CHANGED, 2, 3),
        }
        diff = ConfigDiff(entries)
        result = diff.to_dict()

        assert result == {
            "a": {"diff_type": "added", "left_value": None, "right_value": 1},
            "b": {"diff_type": "changed", "left_value": 2, "right_value": 3},
        }

    def test_repr(self) -> None:
        """repr shows counts."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
            "b": DiffEntry("b", DiffEntryType.REMOVED, left_value=2),
            "c": DiffEntry("c", DiffEntryType.CHANGED, 1, 2),
            "d": DiffEntry("d", DiffEntryType.UNCHANGED, 3, 3),
        }
        diff = ConfigDiff(entries)
        result = repr(diff)
        assert "added=1" in result
        assert "removed=1" in result
        assert "changed=1" in result
        assert "unchanged=1" in result

    def test_str_calls_format(self) -> None:
        """str() returns formatted output."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
        }
        diff = ConfigDiff(entries)
        result = str(diff)
        # Should contain the path and added indicator
        assert "a" in result
        assert "1" in result

    def test_can_be_formatted(self) -> None:
        """ConfigDiff can be formatted with DiffFormat."""
        from rconfig.diff import DiffFormat

        diff = ConfigDiff({})
        fmt = DiffFormat(diff)
        assert isinstance(fmt, DiffFormat)

    def test_immutability(self) -> None:
        """ConfigDiff entries are immutable via MappingProxyType."""
        entries = {
            "a": DiffEntry("a", DiffEntryType.ADDED, right_value=1),
        }
        diff = ConfigDiff(entries)
        # Attempting to modify should raise
        with pytest.raises(TypeError):
            diff._entries["b"] = DiffEntry("b", DiffEntryType.REMOVED, left_value=2)  # type: ignore
