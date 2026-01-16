"""Unit tests for DiffBuilder."""

from __future__ import annotations

import math

import pytest

from rconfig.diff import ConfigDiff, DiffBuilder, DiffEntryType


class TestDiffBuilderManualConstruction:
    """Tests for manually constructing diffs with DiffBuilder."""

    def test_empty_builder(self) -> None:
        """Empty builder produces empty diff."""
        builder = DiffBuilder()
        diff = builder.build()
        assert len(diff) == 0

    def test_add_added(self) -> None:
        """add_added creates an ADDED entry."""
        builder = DiffBuilder()
        builder.add_added("model.dropout", 0.1)
        diff = builder.build()

        assert len(diff) == 1
        entry = diff["model.dropout"]
        assert entry.diff_type == DiffEntryType.ADDED
        assert entry.left_value is None
        assert entry.right_value == 0.1

    def test_add_removed(self) -> None:
        """add_removed creates a REMOVED entry."""
        builder = DiffBuilder()
        builder.add_removed("legacy.param", "old_value")
        diff = builder.build()

        assert len(diff) == 1
        entry = diff["legacy.param"]
        assert entry.diff_type == DiffEntryType.REMOVED
        assert entry.left_value == "old_value"
        assert entry.right_value is None

    def test_add_changed(self) -> None:
        """add_changed creates a CHANGED entry."""
        builder = DiffBuilder()
        builder.add_changed("model.lr", 0.001, 0.01)
        diff = builder.build()

        assert len(diff) == 1
        entry = diff["model.lr"]
        assert entry.diff_type == DiffEntryType.CHANGED
        assert entry.left_value == 0.001
        assert entry.right_value == 0.01

    def test_add_unchanged(self) -> None:
        """add_unchanged creates an UNCHANGED entry."""
        builder = DiffBuilder()
        builder.add_unchanged("model.layers", 4)
        diff = builder.build()

        assert len(diff) == 1
        entry = diff["model.layers"]
        assert entry.diff_type == DiffEntryType.UNCHANGED
        assert entry.left_value == 4
        assert entry.right_value == 4

    def test_chaining(self) -> None:
        """Builder methods return self for chaining."""
        builder = DiffBuilder()
        result = (
            builder.add_added("a", 1)
            .add_removed("b", 2)
            .add_changed("c", 3, 4)
            .add_unchanged("d", 5)
        )

        assert result is builder
        diff = builder.build()
        assert len(diff) == 4

    def test_clear(self) -> None:
        """clear() removes all entries."""
        builder = DiffBuilder()
        builder.add_added("a", 1)
        builder.add_removed("b", 2)
        assert len(builder) == 2

        builder.clear()
        assert len(builder) == 0

        diff = builder.build()
        assert len(diff) == 0

    def test_len(self) -> None:
        """len() returns number of entries in builder."""
        builder = DiffBuilder()
        assert len(builder) == 0

        builder.add_added("a", 1)
        assert len(builder) == 1

        builder.add_removed("b", 2)
        assert len(builder) == 2

    def test_overwrite_entry(self) -> None:
        """Adding same path twice overwrites previous entry."""
        builder = DiffBuilder()
        builder.add_added("a", 1)
        builder.add_removed("a", 2)
        diff = builder.build()

        assert len(diff) == 1
        entry = diff["a"]
        assert entry.diff_type == DiffEntryType.REMOVED
        assert entry.left_value == 2


class TestDiffBuilderComputeDiff:
    """Tests for compute_diff() with Provenance objects."""

    def test_compute_diff_identical(self) -> None:
        """compute_diff with identical configs returns only unchanged."""
        from rconfig.composition import Provenance, ProvenanceEntry

        entries_left = {
            "a": ProvenanceEntry(value=1, file="test.yaml", line=1),
            "b": ProvenanceEntry(value=2, file="test.yaml", line=2),
        }
        entries_right = {
            "a": ProvenanceEntry(value=1, file="test.yaml", line=1),
            "b": ProvenanceEntry(value=2, file="test.yaml", line=2),
        }

        left = Provenance(entries_left)
        right = Provenance(entries_right)

        builder = DiffBuilder()
        diff = builder.compute_diff(left, right)

        assert diff.is_empty()
        assert len(diff.unchanged) == 2

    def test_compute_diff_added(self) -> None:
        """compute_diff detects added entries."""
        from rconfig.composition import Provenance, ProvenanceEntry

        entries_left = {
            "a": ProvenanceEntry(value=1, file="test.yaml", line=1),
        }
        entries_right = {
            "a": ProvenanceEntry(value=1, file="test.yaml", line=1),
            "b": ProvenanceEntry(value=2, file="test.yaml", line=2),
        }

        left = Provenance(entries_left)
        right = Provenance(entries_right)

        builder = DiffBuilder()
        diff = builder.compute_diff(left, right)

        assert len(diff.added) == 1
        assert "b" in diff.added
        assert diff.added["b"].right_value == 2

    def test_compute_diff_removed(self) -> None:
        """compute_diff detects removed entries."""
        from rconfig.composition import Provenance, ProvenanceEntry

        entries_left = {
            "a": ProvenanceEntry(value=1, file="test.yaml", line=1),
            "b": ProvenanceEntry(value=2, file="test.yaml", line=2),
        }
        entries_right = {
            "a": ProvenanceEntry(value=1, file="test.yaml", line=1),
        }

        left = Provenance(entries_left)
        right = Provenance(entries_right)

        builder = DiffBuilder()
        diff = builder.compute_diff(left, right)

        assert len(diff.removed) == 1
        assert "b" in diff.removed
        assert diff.removed["b"].left_value == 2

    def test_compute_diff_changed(self) -> None:
        """compute_diff detects changed entries."""
        from rconfig.composition import Provenance, ProvenanceEntry

        entries_left = {
            "a": ProvenanceEntry(value=1, file="test.yaml", line=1),
            "b": ProvenanceEntry(value="old", file="test.yaml", line=2),
        }
        entries_right = {
            "a": ProvenanceEntry(value=1, file="test.yaml", line=1),
            "b": ProvenanceEntry(value="new", file="test.yaml", line=2),
        }

        left = Provenance(entries_left)
        right = Provenance(entries_right)

        builder = DiffBuilder()
        diff = builder.compute_diff(left, right)

        assert len(diff.changed) == 1
        assert "b" in diff.changed
        assert diff.changed["b"].left_value == "old"
        assert diff.changed["b"].right_value == "new"

    def test_compute_diff_preserves_provenance(self) -> None:
        """compute_diff preserves provenance entries."""
        from rconfig.composition import Provenance, ProvenanceEntry

        left_entry = ProvenanceEntry(value=1, file="left.yaml", line=10)
        right_entry = ProvenanceEntry(value=2, file="right.yaml", line=20)

        left = Provenance({"a": left_entry})
        right = Provenance({"a": right_entry})

        builder = DiffBuilder()
        diff = builder.compute_diff(left, right)

        assert len(diff.changed) == 1
        entry = diff.changed["a"]
        assert entry.left_provenance is left_entry
        assert entry.right_provenance is right_entry

    def test_compute_diff_complex_scenario(self) -> None:
        """compute_diff handles mixed changes correctly."""
        from rconfig.composition import Provenance, ProvenanceEntry

        entries_left = {
            "unchanged": ProvenanceEntry(value="same", file="test.yaml", line=1),
            "changed": ProvenanceEntry(value="old", file="test.yaml", line=2),
            "removed": ProvenanceEntry(value="gone", file="test.yaml", line=3),
        }
        entries_right = {
            "unchanged": ProvenanceEntry(value="same", file="test.yaml", line=1),
            "changed": ProvenanceEntry(value="new", file="test.yaml", line=2),
            "added": ProvenanceEntry(value="new_entry", file="test.yaml", line=4),
        }

        left = Provenance(entries_left)
        right = Provenance(entries_right)

        builder = DiffBuilder()
        diff = builder.compute_diff(left, right)

        assert len(diff.unchanged) == 1
        assert len(diff.changed) == 1
        assert len(diff.removed) == 1
        assert len(diff.added) == 1

        assert "unchanged" in diff.unchanged
        assert "changed" in diff.changed
        assert "removed" in diff.removed
        assert "added" in diff.added

    def test_compute_diff_nan_values(self) -> None:
        """compute_diff treats NaN == NaN as unchanged."""
        from rconfig.composition import Provenance, ProvenanceEntry

        nan = float("nan")
        entries_left = {"a": ProvenanceEntry(value=nan, file="test.yaml", line=1)}
        entries_right = {"a": ProvenanceEntry(value=nan, file="test.yaml", line=1)}

        left = Provenance(entries_left)
        right = Provenance(entries_right)

        builder = DiffBuilder()
        diff = builder.compute_diff(left, right)

        # NaN should be considered equal to NaN for diffing purposes
        assert len(diff.unchanged) == 1
        assert "a" in diff.unchanged

    def test_compute_diff_returns_configdiff(self) -> None:
        """compute_diff returns a ConfigDiff instance."""
        from rconfig.composition import Provenance, ProvenanceEntry

        left = Provenance({"a": ProvenanceEntry(value=1, file="test.yaml", line=1)})
        right = Provenance({"a": ProvenanceEntry(value=1, file="test.yaml", line=1)})

        builder = DiffBuilder()
        diff = builder.compute_diff(left, right)

        assert isinstance(diff, ConfigDiff)
