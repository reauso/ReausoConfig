"""Integration tests for config diffing feature."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

import rconfig as rc


class TestDiffWithRealFiles:
    """Integration tests for rc.diff() with real YAML files."""

    def test_diff_identical_configs(self, tmp_path: Path) -> None:
        """Diffing identical configs returns empty diff."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                  layers: 4
                """
            )
        )

        diff = rc.diff(config_file, config_file)

        assert diff.is_empty()
        assert len(diff.added) == 0
        assert len(diff.removed) == 0
        assert len(diff.changed) == 0
        assert len(diff.unchanged) == 2  # model.lr and model.layers

    def test_diff_added_entries(self, tmp_path: Path) -> None:
        """Diffing detects added entries."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                """
            )
        )

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                  dropout: 0.1
                """
            )
        )

        diff = rc.diff(config_v1, config_v2)

        assert not diff.is_empty()
        assert len(diff.added) == 1
        assert "model.dropout" in diff.added
        assert diff.added["model.dropout"].right_value == 0.1

    def test_diff_removed_entries(self, tmp_path: Path) -> None:
        """Diffing detects removed entries."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                  legacy_param: "old"
                """
            )
        )

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                """
            )
        )

        diff = rc.diff(config_v1, config_v2)

        assert not diff.is_empty()
        assert len(diff.removed) == 1
        assert "model.legacy_param" in diff.removed
        assert diff.removed["model.legacy_param"].left_value == "old"

    def test_diff_changed_entries(self, tmp_path: Path) -> None:
        """Diffing detects changed entries."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text(
            dedent(
                """
                model:
                  lr: 0.001
                  batch_size: 32
                """
            )
        )

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                  batch_size: 64
                """
            )
        )

        diff = rc.diff(config_v1, config_v2)

        assert not diff.is_empty()
        assert len(diff.changed) == 2
        assert "model.lr" in diff.changed
        assert diff.changed["model.lr"].left_value == 0.001
        assert diff.changed["model.lr"].right_value == 0.01

    def test_diff_mixed_changes(self, tmp_path: Path) -> None:
        """Diffing handles mixed changes correctly."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text(
            dedent(
                """
                model:
                  lr: 0.001
                  legacy: true
                data:
                  path: "/data"
                """
            )
        )

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                  dropout: 0.1
                data:
                  path: "/data"
                """
            )
        )

        diff = rc.diff(config_v1, config_v2)

        assert len(diff.added) == 1  # model.dropout
        assert len(diff.removed) == 1  # model.legacy
        assert len(diff.changed) == 1  # model.lr
        assert len(diff.unchanged) == 1  # data.path


class TestDiffWithOverrides:
    """Integration tests for rc.diff() with overrides."""

    def test_diff_same_file_different_overrides(self, tmp_path: Path) -> None:
        """Diff same file with different overrides shows changes."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            dedent(
                """
                model:
                  lr: 0.001
                  layers: 4
                """
            )
        )

        diff = rc.diff(
            config_file,
            config_file,
            left_overrides={"model.lr": 0.001},
            right_overrides={"model.lr": 0.01},
        )

        assert not diff.is_empty()
        assert len(diff.changed) == 1
        assert "model.lr" in diff.changed
        assert diff.changed["model.lr"].left_value == 0.001
        assert diff.changed["model.lr"].right_value == 0.01

    def test_diff_with_different_override_values(self, tmp_path: Path) -> None:
        """Override changes value for diffing."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            dedent(
                """
                model:
                  lr: 0.001
                  dropout: 0.1
                """
            )
        )

        diff = rc.diff(
            config_file,
            config_file,
            right_overrides={"model.dropout": 0.2},
        )

        assert not diff.is_empty()
        assert len(diff.changed) == 1
        assert "model.dropout" in diff.changed


class TestDiffWithInnerPath:
    """Integration tests for rc.diff() with inner_path.

    Note: The inner_path parameter is primarily for lazy loading optimization.
    It affects which files are loaded, but paths in the diff still use full paths.
    """

    def test_diff_full_configs(self, tmp_path: Path) -> None:
        """Diff full configs shows all changes."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text(
            dedent(
                """
                model:
                  lr: 0.001
                  layers: 4
                data:
                  batch_size: 32
                """
            )
        )

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                  layers: 8
                data:
                  batch_size: 64
                """
            )
        )

        # Diff the full configs
        diff = rc.diff(config_v1, config_v2)

        # All three paths changed
        assert len(diff.changed) == 3
        assert "model.lr" in diff.changed
        assert "model.layers" in diff.changed
        assert "data.batch_size" in diff.changed

    def test_diff_with_path_filter(self, tmp_path: Path) -> None:
        """Use path filter to compare only specific section.

        To compare only the 'model' section, use the format builder's
        for_path() filter instead of inner_path.
        """
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text(
            dedent(
                """
                model:
                  lr: 0.001
                  layers: 4
                data:
                  batch_size: 32
                """
            )
        )

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                  layers: 8
                data:
                  batch_size: 64
                """
            )
        )

        diff = rc.diff(config_v1, config_v2)

        # Use path filter to show only model section in output
        output = rc.format(diff).for_path("model.*").terminal()

        assert "model.lr" in output
        assert "model.layers" in output
        # data.batch_size should be filtered out of output
        assert "data.batch_size" not in output


class TestDiffWithProvenance:
    """Integration tests for diffing with provenance objects."""

    def test_diff_with_provenance_objects(self, tmp_path: Path) -> None:
        """rc.diff accepts Provenance objects directly."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text(
            dedent(
                """
                model:
                  lr: 0.001
                """
            )
        )

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                """
            )
        )

        # Get provenance objects first
        prov_v1 = rc.get_provenance(config_v1)
        prov_v2 = rc.get_provenance(config_v2)

        # Use provenance objects for diff
        diff = rc.diff(prov_v1, prov_v2)

        assert len(diff.changed) == 1
        assert "model.lr" in diff.changed

    def test_diff_preserves_provenance_info(self, tmp_path: Path) -> None:
        """Diff entries contain provenance information."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text(
            dedent(
                """
                model:
                  lr: 0.001
                """
            )
        )

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                """
            )
        )

        diff = rc.diff(config_v1, config_v2)

        entry = diff.changed["model.lr"]
        assert entry.left_provenance is not None
        assert entry.right_provenance is not None
        assert "v1.yaml" in entry.left_provenance.file
        assert "v2.yaml" in entry.right_provenance.file


class TestDiffOutputFormats:
    """Integration tests for diff output formatting."""

    def test_terminal_output(self, tmp_path: Path) -> None:
        """terminal() produces readable output."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text("model:\n  lr: 0.001\n")

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text("model:\n  lr: 0.01\n  dropout: 0.1\n")

        diff = rc.diff(config_v1, config_v2)
        output = rc.format(diff).terminal()

        assert "+ model.dropout" in output
        assert "~ model.lr" in output
        assert "0.001" in output
        assert "0.01" in output

    def test_tree_output(self, tmp_path: Path) -> None:
        """tree() produces grouped output."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text("model:\n  lr: 0.001\n  legacy: true\n")

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text("model:\n  lr: 0.01\n  dropout: 0.1\n")

        diff = rc.diff(config_v1, config_v2)
        output = rc.format(diff).tree()

        assert "ConfigDiff:" in output
        assert "Added:" in output
        assert "Removed:" in output
        assert "Changed:" in output

    def test_markdown_output(self, tmp_path: Path) -> None:
        """markdown() produces table output."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text("model:\n  lr: 0.001\n")

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text("model:\n  lr: 0.01\n")

        diff = rc.diff(config_v1, config_v2)
        output = rc.format(diff).markdown()

        assert "| Type |" in output
        assert "| Path |" in output
        assert "| ~ |" in output
        assert "model.lr" in output

    def test_json_output(self, tmp_path: Path) -> None:
        """json() produces dict output."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text("model:\n  lr: 0.001\n")

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text("model:\n  lr: 0.01\n")

        diff = rc.diff(config_v1, config_v2)
        output = rc.format(diff).json()

        assert isinstance(output, dict)
        assert "model.lr" in output
        assert output["model.lr"]["diff_type"] == "changed"

    def test_format_with_options(self, tmp_path: Path) -> None:
        """Format options affect output."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text("model:\n  lr: 0.001\n")

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text("model:\n  lr: 0.01\n")

        diff = rc.diff(config_v1, config_v2)

        # With provenance
        output_with_prov = rc.format(diff).show_provenance().terminal()
        assert "v1.yaml" in output_with_prov or "v2.yaml" in output_with_prov

        # Hide counts
        output_no_counts = rc.format(diff).hide_counts().terminal()
        assert "Changed: 1" not in output_no_counts

    def test_str_uses_default_format(self, tmp_path: Path) -> None:
        """str(diff) uses default format."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text("model:\n  lr: 0.001\n")

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text("model:\n  lr: 0.01\n")

        diff = rc.diff(config_v1, config_v2)
        output = str(diff)

        # Default is flat layout
        assert "~ model.lr" in output


class TestDiffPresets:
    """Integration tests for diff presets."""

    def test_changes_only_preset(self, tmp_path: Path) -> None:
        """changes_only preset hides unchanged entries."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text("model:\n  lr: 0.001\n  layers: 4\n")

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text("model:\n  lr: 0.01\n  layers: 4\n")

        diff = rc.diff(config_v1, config_v2)
        output = rc.format(diff).changes_only().terminal()

        assert "model.lr" in output
        assert "model.layers" not in output  # Unchanged, should be hidden

    def test_with_context_preset(self, tmp_path: Path) -> None:
        """with_context preset shows unchanged entries."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text("model:\n  lr: 0.001\n  layers: 4\n")

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text("model:\n  lr: 0.01\n  layers: 4\n")

        diff = rc.diff(config_v1, config_v2)
        output = rc.format(diff).with_context().terminal()

        assert "model.lr" in output
        assert "model.layers" in output  # Unchanged, should be visible

    def test_full_preset(self, tmp_path: Path) -> None:
        """full preset shows everything including provenance."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text("model:\n  lr: 0.001\n")

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text("model:\n  lr: 0.01\n")

        diff = rc.diff(config_v1, config_v2)
        output = rc.format(diff).full().terminal()

        assert "model.lr" in output
        # Should include provenance (file info)
        assert ".yaml" in output

    def test_summary_preset(self, tmp_path: Path) -> None:
        """summary preset shows only counts."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text("model:\n  lr: 0.001\n  layers: 4\n")

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text("model:\n  lr: 0.01\n  dropout: 0.1\n")

        diff = rc.diff(config_v1, config_v2)
        output = rc.format(diff).summary().terminal()

        # Should only show counts, not individual entries
        assert "Added: 1" in output or "Changed: 1" in output
        # Entry paths should not be visible
        assert "+" not in output or "- " not in output


class TestDiffEmptyConfigs:
    """Integration tests for edge cases with empty configs."""

    def test_diff_empty_configs(self, tmp_path: Path) -> None:
        """Diffing empty configs returns empty diff."""
        config1 = tmp_path / "empty1.yaml"
        config1.write_text("{}")

        config2 = tmp_path / "empty2.yaml"
        config2.write_text("{}")

        diff = rc.diff(config1, config2)
        assert diff.is_empty()
        assert len(diff) == 0

    def test_diff_empty_vs_nonempty(self, tmp_path: Path) -> None:
        """Diffing empty vs non-empty shows all as added."""
        config_empty = tmp_path / "empty.yaml"
        config_empty.write_text("{}")

        config_full = tmp_path / "full.yaml"
        config_full.write_text("model:\n  lr: 0.01\n")

        diff = rc.diff(config_empty, config_full)
        assert not diff.is_empty()
        assert len(diff.added) == 1
        assert "model.lr" in diff.added

    def test_diff_nonempty_vs_empty(self, tmp_path: Path) -> None:
        """Diffing non-empty vs empty shows all as removed."""
        config_full = tmp_path / "full.yaml"
        config_full.write_text("model:\n  lr: 0.01\n")

        config_empty = tmp_path / "empty.yaml"
        config_empty.write_text("{}")

        diff = rc.diff(config_full, config_empty)
        assert not diff.is_empty()
        assert len(diff.removed) == 1
        assert "model.lr" in diff.removed
