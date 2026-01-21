"""Integration tests for formatting preset registries."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

import rconfig as rc
from rconfig.provenance.formatting import get_provenance_registry
from rconfig.diff.formatting import get_diff_registry


class TestProvenancePresetIntegration:
    """Integration tests for provenance preset registration and usage."""

    @pytest.fixture(autouse=True)
    def clear_registries(self):
        """Clear custom presets before and after each test."""
        get_provenance_registry().clear_presets()
        get_diff_registry().clear_presets()
        yield
        get_provenance_registry().clear_presets()
        get_diff_registry().clear_presets()

    def test_ProvenanceFormat__StringPreset__AppliesCorrectly(self, tmp_path: Path) -> None:
        """Test that string-based preset() method applies presets correctly."""
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

        prov = rc.get_provenance(config_file)

        # Test various presets work
        result_minimal = str(rc.format(prov).preset("minimal"))
        result_full = str(rc.format(prov).preset("full"))
        result_values = str(rc.format(prov).preset("values"))

        # Minimal should have fewer details than full
        assert len(result_minimal) < len(result_full)
        # Values should not contain file info
        assert "config.yaml" not in result_values

    def test_ProvenanceFormat__NamedMethod__AppliesCorrectly(self, tmp_path: Path) -> None:
        """Test that named preset methods work correctly."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                """
            )
        )

        prov = rc.get_provenance(config_file)

        # Named methods should produce same output as preset()
        result_minimal_method = str(rc.format(prov).minimal())
        result_minimal_preset = str(rc.format(prov).preset("minimal"))

        assert result_minimal_method == result_minimal_preset

    def test_ProvenanceFormat__CustomPreset__AppliesCorrectly(self, tmp_path: Path) -> None:
        """Test that custom presets can be registered and used."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                """
            )
        )

        # Register custom preset
        rc.register_provenance_preset(
            "paths_only",
            lambda: rc.ProvenanceFormatContext(
                show_paths=True,
                show_values=False,
                show_files=False,
                show_lines=False,
                show_source_type=False,
                show_chain=False,
                show_overrides=False,
                show_targets=False,
            ),
            "Show only paths",
        )

        prov = rc.get_provenance(config_file)
        result = str(rc.format(prov).preset("paths_only"))

        # Should contain path but not value
        assert "model.lr" in result
        assert "0.01" not in result

    def test_ProvenanceFormat__UnknownPreset__RaisesValueError(self, tmp_path: Path) -> None:
        """Test that unknown preset raises ValueError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                """
            )
        )

        prov = rc.get_provenance(config_file)

        with pytest.raises(ValueError, match="Unknown preset"):
            rc.format(prov).preset("nonexistent")

    def test_register_provenance_preset__ViaPublicAPI__Works(self) -> None:
        """Test that register_provenance_preset works via rc module."""
        rc.register_provenance_preset(
            "test_preset",
            lambda: rc.ProvenanceFormatContext(show_paths=True),
            "Test preset",
        )

        presets = rc.known_provenance_presets()

        assert "test_preset" in presets
        assert presets["test_preset"].description == "Test preset"
        assert not presets["test_preset"].builtin

    def test_provenance_preset_decorator__RegistersPreset(self) -> None:
        """Test that @provenance_preset decorator registers preset."""

        @rc.provenance_preset("decorated_preset", "Decorated test preset")
        def my_preset() -> rc.ProvenanceFormatContext:
            return rc.ProvenanceFormatContext(show_paths=True, show_values=False)

        presets = rc.known_provenance_presets()

        assert "decorated_preset" in presets
        assert presets["decorated_preset"].description == "Decorated test preset"

        # Verify the factory returns correct context
        ctx = presets["decorated_preset"].factory()
        assert ctx.show_paths is True
        assert ctx.show_values is False

    def test_known_provenance_presets__ReturnsAllPresets(self) -> None:
        """Test that known_provenance_presets returns all presets."""
        presets = rc.known_provenance_presets()

        # Should include all built-in presets
        assert "default" in presets
        assert "minimal" in presets
        assert "compact" in presets
        assert "full" in presets
        assert "values" in presets
        assert "help" in presets
        assert "deprecations" in presets

    def test_known_provenance_presets__IncludesBuiltins(self) -> None:
        """Test that all built-in presets are marked as builtin."""
        presets = rc.known_provenance_presets()

        for name in ["default", "minimal", "compact", "full", "values", "help", "deprecations"]:
            assert presets[name].builtin is True


class TestDiffPresetIntegration:
    """Integration tests for diff preset registration and usage."""

    @pytest.fixture(autouse=True)
    def clear_registries(self):
        """Clear custom presets before and after each test."""
        get_provenance_registry().clear_presets()
        get_diff_registry().clear_presets()
        yield
        get_provenance_registry().clear_presets()
        get_diff_registry().clear_presets()

    def test_DiffFormat__StringPreset__AppliesCorrectly(self, tmp_path: Path) -> None:
        """Test that string-based preset() method applies presets correctly."""
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
                  lr: 0.02
                  dropout: 0.1
                """
            )
        )

        diff = rc.diff(config_v1, config_v2)

        # Test various presets work
        result_default = str(rc.format(diff).preset("default"))
        result_summary = str(rc.format(diff).preset("summary"))

        # Summary should be shorter (only counts, no entries)
        assert len(result_summary) < len(result_default)

    def test_DiffFormat__NamedMethod__AppliesCorrectly(self, tmp_path: Path) -> None:
        """Test that named preset methods work correctly."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text("model:\n  lr: 0.01\n")

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text("model:\n  lr: 0.02\n")

        diff = rc.diff(config_v1, config_v2)

        # Named methods should produce same output as preset()
        result_changes_method = str(rc.format(diff).changes_only())
        result_changes_preset = str(rc.format(diff).preset("changes_only"))

        assert result_changes_method == result_changes_preset

    def test_DiffFormat__CustomPreset__AppliesCorrectly(self, tmp_path: Path) -> None:
        """Test that custom presets can be registered and used."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text("model:\n  lr: 0.01\n")

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text("model:\n  lr: 0.01\n  new_param: true\n")

        # Register custom preset
        rc.register_diff_preset(
            "added_only",
            lambda: rc.DiffFormatContext(
                show_added=True,
                show_removed=False,
                show_changed=False,
                show_unchanged=False,
            ),
            "Show only added entries",
        )

        diff = rc.diff(config_v1, config_v2)
        result = str(rc.format(diff).preset("added_only"))

        # Should show added entry
        assert "new_param" in result

    def test_DiffFormat__UnknownPreset__RaisesValueError(self, tmp_path: Path) -> None:
        """Test that unknown preset raises ValueError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("model:\n  lr: 0.01\n")

        diff = rc.diff(config_file, config_file)

        with pytest.raises(ValueError, match="Unknown preset"):
            rc.format(diff).preset("nonexistent")

    def test_register_diff_preset__ViaPublicAPI__Works(self) -> None:
        """Test that register_diff_preset works via rc module."""
        rc.register_diff_preset(
            "test_diff_preset",
            lambda: rc.DiffFormatContext(show_added=True),
            "Test diff preset",
        )

        presets = rc.known_diff_presets()

        assert "test_diff_preset" in presets
        assert presets["test_diff_preset"].description == "Test diff preset"
        assert not presets["test_diff_preset"].builtin

    def test_diff_preset_decorator__RegistersPreset(self) -> None:
        """Test that @diff_preset decorator registers preset."""

        @rc.diff_preset("decorated_diff_preset", "Decorated diff preset")
        def my_diff_preset() -> rc.DiffFormatContext:
            return rc.DiffFormatContext(show_added=True, show_removed=False)

        presets = rc.known_diff_presets()

        assert "decorated_diff_preset" in presets
        assert presets["decorated_diff_preset"].description == "Decorated diff preset"

        # Verify the factory returns correct context
        ctx = presets["decorated_diff_preset"].factory()
        assert ctx.show_added is True
        assert ctx.show_removed is False

    def test_known_diff_presets__ReturnsAllPresets(self) -> None:
        """Test that known_diff_presets returns all presets."""
        presets = rc.known_diff_presets()

        # Should include all built-in presets
        assert "default" in presets
        assert "changes_only" in presets
        assert "with_context" in presets
        assert "full" in presets
        assert "summary" in presets

    def test_known_diff_presets__IncludesBuiltins(self) -> None:
        """Test that all built-in presets are marked as builtin."""
        presets = rc.known_diff_presets()

        for name in ["default", "changes_only", "with_context", "full", "summary"]:
            assert presets[name].builtin is True


class TestBuiltinProtection:
    """Tests for built-in preset protection."""

    @pytest.fixture(autouse=True)
    def clear_registries(self):
        """Clear custom presets before and after each test."""
        get_provenance_registry().clear_presets()
        get_diff_registry().clear_presets()
        yield
        get_provenance_registry().clear_presets()
        get_diff_registry().clear_presets()

    def test_register_provenance_preset__BuiltinName__RaisesValueError(self) -> None:
        """Test that registering over a built-in preset raises ValueError."""
        with pytest.raises(ValueError, match="built-in preset"):
            rc.register_provenance_preset(
                "minimal",
                lambda: rc.ProvenanceFormatContext(),
                "Override attempt",
            )

    def test_unregister_provenance_preset__BuiltinName__RaisesValueError(self) -> None:
        """Test that unregistering a built-in preset raises ValueError."""
        with pytest.raises(ValueError, match="built-in preset"):
            rc.unregister_provenance_preset("minimal")

    def test_register_diff_preset__BuiltinName__RaisesValueError(self) -> None:
        """Test that registering over a built-in diff preset raises ValueError."""
        with pytest.raises(ValueError, match="built-in preset"):
            rc.register_diff_preset(
                "changes_only",
                lambda: rc.DiffFormatContext(),
                "Override attempt",
            )

    def test_unregister_diff_preset__BuiltinName__RaisesValueError(self) -> None:
        """Test that unregistering a built-in diff preset raises ValueError."""
        with pytest.raises(ValueError, match="built-in preset"):
            rc.unregister_diff_preset("changes_only")


class TestProvenanceLayoutIntegration:
    """Integration tests for provenance layout registration and usage."""

    @pytest.fixture(autouse=True)
    def clear_registries(self):
        """Clear custom layouts before and after each test."""
        get_provenance_registry().clear_layouts()
        get_diff_registry().clear_layouts()
        yield
        get_provenance_registry().clear_layouts()
        get_diff_registry().clear_layouts()

    def test_ProvenanceFormat__StringLayout__AppliesCorrectly(self, tmp_path: Path) -> None:
        """Test that string-based layout() method applies layouts correctly."""
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

        prov = rc.get_provenance(config_file)

        # Test various layouts work
        result_tree = str(rc.format(prov).layout("tree"))
        result_flat = str(rc.format(prov).layout("flat"))
        result_markdown = str(rc.format(prov).layout("markdown"))

        # All should contain the path
        assert "model.lr" in result_tree
        assert "model.lr" in result_flat
        assert "model.lr" in result_markdown

        # Markdown should have table markers
        assert "|" in result_markdown

    def test_ProvenanceFormat__ConvenienceMethod__AppliesCorrectly(self, tmp_path: Path) -> None:
        """Test that convenience layout methods work correctly."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                """
            )
        )

        prov = rc.get_provenance(config_file)

        # Convenience methods should produce same output as layout()
        result_tree_method = str(rc.format(prov).tree())
        result_tree_layout = str(rc.format(prov).layout("tree"))

        assert result_tree_method == result_tree_layout

    def test_ProvenanceFormat__UnknownLayout__RaisesValueError(self, tmp_path: Path) -> None:
        """Test that unknown layout raises ValueError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            dedent(
                """
                model:
                  lr: 0.01
                """
            )
        )

        prov = rc.get_provenance(config_file)

        with pytest.raises(ValueError, match="Unknown layout"):
            rc.format(prov).layout("nonexistent")

    def test_register_provenance_layout__ViaPublicAPI__Works(self) -> None:
        """Test that register_provenance_layout works via rc module."""
        from rconfig.provenance.formatting import ProvenanceLayout, ProvenanceDisplayModel

        class TestLayout(ProvenanceLayout):
            def render(self, model: ProvenanceDisplayModel) -> str:
                return "test output"

        rc.register_provenance_layout(
            "test_layout",
            lambda: TestLayout(),
            "Test layout",
        )

        layouts = rc.known_provenance_layouts()

        assert "test_layout" in layouts
        assert layouts["test_layout"].description == "Test layout"
        assert not layouts["test_layout"].builtin

    def test_provenance_layout_decorator__RegistersLayout(self) -> None:
        """Test that @provenance_layout decorator registers layout."""
        from rconfig.provenance.formatting import ProvenanceLayout, ProvenanceDisplayModel

        class DecoratedLayout(ProvenanceLayout):
            def render(self, model: ProvenanceDisplayModel) -> str:
                return "decorated output"

        @rc.provenance_layout("decorated_layout", "Decorated test layout")
        def my_layout() -> ProvenanceLayout:
            return DecoratedLayout()

        layouts = rc.known_provenance_layouts()

        assert "decorated_layout" in layouts
        assert layouts["decorated_layout"].description == "Decorated test layout"

        # Verify the factory returns correct layout
        layout = layouts["decorated_layout"].factory()
        assert isinstance(layout, ProvenanceLayout)

    def test_known_provenance_layouts__ReturnsAllLayouts(self) -> None:
        """Test that known_provenance_layouts returns all layouts."""
        layouts = rc.known_provenance_layouts()

        # Should include all built-in layouts
        assert "tree" in layouts
        assert "flat" in layouts
        assert "markdown" in layouts

    def test_known_provenance_layouts__IncludesBuiltins(self) -> None:
        """Test that all built-in layouts are marked as builtin."""
        layouts = rc.known_provenance_layouts()

        for name in ["tree", "flat", "markdown"]:
            assert layouts[name].builtin is True


class TestDiffLayoutIntegration:
    """Integration tests for diff layout registration and usage."""

    @pytest.fixture(autouse=True)
    def clear_registries(self):
        """Clear custom layouts before and after each test."""
        get_provenance_registry().clear_layouts()
        get_diff_registry().clear_layouts()
        yield
        get_provenance_registry().clear_layouts()
        get_diff_registry().clear_layouts()

    def test_DiffFormat__StringLayout__AppliesCorrectly(self, tmp_path: Path) -> None:
        """Test that string-based layout() method applies layouts correctly."""
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
                  lr: 0.02
                  dropout: 0.1
                """
            )
        )

        diff = rc.diff(config_v1, config_v2)

        # Test various layouts work
        result_flat = str(rc.format(diff).layout("flat"))
        result_tree = str(rc.format(diff).layout("tree"))
        result_markdown = str(rc.format(diff).layout("markdown"))

        # All should contain some indication of changes
        assert "lr" in result_flat or "dropout" in result_flat
        assert "lr" in result_tree or "dropout" in result_tree
        assert "|" in result_markdown  # Table markers

    def test_DiffFormat__ConvenienceMethod__AppliesCorrectly(self, tmp_path: Path) -> None:
        """Test that convenience layout methods work correctly."""
        config_v1 = tmp_path / "v1.yaml"
        config_v1.write_text("model:\n  lr: 0.01\n")

        config_v2 = tmp_path / "v2.yaml"
        config_v2.write_text("model:\n  lr: 0.02\n")

        diff = rc.diff(config_v1, config_v2)

        # tree() should produce same output as layout("tree")
        result_tree_method = str(rc.format(diff).tree())
        result_tree_layout = str(rc.format(diff).layout("tree"))

        assert result_tree_method == result_tree_layout

    def test_DiffFormat__UnknownLayout__RaisesValueError(self, tmp_path: Path) -> None:
        """Test that unknown layout raises ValueError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("model:\n  lr: 0.01\n")

        diff = rc.diff(config_file, config_file)

        with pytest.raises(ValueError, match="Unknown layout"):
            rc.format(diff).layout("nonexistent")

    def test_register_diff_layout__ViaPublicAPI__Works(self) -> None:
        """Test that register_diff_layout works via rc module."""
        from rconfig.diff.formatting import DiffLayout, DiffDisplayModel

        class TestDiffLayout(DiffLayout):
            def render(self, model: DiffDisplayModel) -> str:
                return "test diff output"

        rc.register_diff_layout(
            "test_diff_layout",
            lambda: TestDiffLayout(),
            "Test diff layout",
        )

        layouts = rc.known_diff_layouts()

        assert "test_diff_layout" in layouts
        assert layouts["test_diff_layout"].description == "Test diff layout"
        assert not layouts["test_diff_layout"].builtin

    def test_diff_layout_decorator__RegistersLayout(self) -> None:
        """Test that @diff_layout decorator registers layout."""
        from rconfig.diff.formatting import DiffLayout, DiffDisplayModel

        class DecoratedDiffLayout(DiffLayout):
            def render(self, model: DiffDisplayModel) -> str:
                return "decorated diff output"

        @rc.diff_layout("decorated_diff_layout", "Decorated diff layout")
        def my_diff_layout() -> DiffLayout:
            return DecoratedDiffLayout()

        layouts = rc.known_diff_layouts()

        assert "decorated_diff_layout" in layouts
        assert layouts["decorated_diff_layout"].description == "Decorated diff layout"

        # Verify the factory returns correct layout
        layout = layouts["decorated_diff_layout"].factory()
        assert isinstance(layout, DiffLayout)

    def test_known_diff_layouts__ReturnsAllLayouts(self) -> None:
        """Test that known_diff_layouts returns all layouts."""
        layouts = rc.known_diff_layouts()

        # Should include all built-in layouts
        assert "flat" in layouts
        assert "tree" in layouts
        assert "markdown" in layouts

    def test_known_diff_layouts__IncludesBuiltins(self) -> None:
        """Test that all built-in layouts are marked as builtin."""
        layouts = rc.known_diff_layouts()

        for name in ["flat", "tree", "markdown"]:
            assert layouts[name].builtin is True


class TestBuiltinLayoutProtection:
    """Tests for built-in layout protection."""

    @pytest.fixture(autouse=True)
    def clear_registries(self):
        """Clear custom layouts before and after each test."""
        get_provenance_registry().clear_layouts()
        get_diff_registry().clear_layouts()
        yield
        get_provenance_registry().clear_layouts()
        get_diff_registry().clear_layouts()

    def test_register_provenance_layout__BuiltinName__RaisesValueError(self) -> None:
        """Test that registering over a built-in layout raises ValueError."""
        from rconfig.provenance.formatting import ProvenanceTreeLayout

        with pytest.raises(ValueError, match="built-in layout"):
            rc.register_provenance_layout(
                "tree",
                lambda: ProvenanceTreeLayout(),
                "Override attempt",
            )

    def test_unregister_provenance_layout__BuiltinName__RaisesValueError(self) -> None:
        """Test that unregistering a built-in layout raises ValueError."""
        with pytest.raises(ValueError, match="built-in layout"):
            rc.unregister_provenance_layout("tree")

    def test_register_diff_layout__BuiltinName__RaisesValueError(self) -> None:
        """Test that registering over a built-in diff layout raises ValueError."""
        from rconfig.diff.formatting import DiffFlatLayout

        with pytest.raises(ValueError, match="built-in layout"):
            rc.register_diff_layout(
                "flat",
                lambda: DiffFlatLayout(),
                "Override attempt",
            )

    def test_unregister_diff_layout__BuiltinName__RaisesValueError(self) -> None:
        """Test that unregistering a built-in diff layout raises ValueError."""
        with pytest.raises(ValueError, match="built-in layout"):
            rc.unregister_diff_layout("flat")