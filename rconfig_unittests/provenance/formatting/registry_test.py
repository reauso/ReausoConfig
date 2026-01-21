"""Tests for ProvenanceRegistry and preset/layout management."""

from dataclasses import FrozenInstanceError
from types import MappingProxyType
from unittest import TestCase

from rconfig.provenance.formatting import (
    ProvenanceFormatContext,
    ProvenanceLayout,
    ProvenanceLayoutEntry,
    ProvenancePresetEntry,
    ProvenanceRegistry,
    ProvenanceTreeLayout,
    get_provenance_registry,
)


class ProvenancePresetEntryTests(TestCase):
    """Tests for ProvenancePresetEntry dataclass."""

    def test_ProvenancePresetEntry__Creation__StoresValues(self) -> None:
        """Test that entry stores all provided values."""
        factory = lambda: ProvenanceFormatContext()
        entry = ProvenancePresetEntry(
            name="test",
            factory=factory,
            description="Test description",
            builtin=True,
        )

        self.assertEqual(entry.name, "test")
        self.assertEqual(entry.factory, factory)
        self.assertEqual(entry.description, "Test description")
        self.assertTrue(entry.builtin)

    def test_ProvenancePresetEntry__DefaultValues__HasCorrectDefaults(self) -> None:
        """Test that entry has correct default values."""
        entry = ProvenancePresetEntry(
            name="test",
            factory=lambda: ProvenanceFormatContext(),
        )

        self.assertEqual(entry.description, "")
        self.assertFalse(entry.builtin)

    def test_ProvenancePresetEntry__Frozen__CannotModify(self) -> None:
        """Test that entry is immutable."""
        entry = ProvenancePresetEntry(
            name="test",
            factory=lambda: ProvenanceFormatContext(),
        )

        with self.assertRaises(FrozenInstanceError):
            entry.name = "changed"  # type: ignore


class ProvenanceRegistryTests(TestCase):
    """Tests for ProvenanceRegistry singleton."""

    def setUp(self) -> None:
        """Clear custom presets before each test."""
        get_provenance_registry().clear_presets()

    def tearDown(self) -> None:
        """Clear custom presets after each test."""
        get_provenance_registry().clear_presets()

    def test_ProvenanceRegistry__Singleton__ReturnsSameInstance(self) -> None:
        """Test that registry is a singleton."""
        registry1 = ProvenanceRegistry()
        registry2 = ProvenanceRegistry()

        self.assertIs(registry1, registry2)

    def test_get_provenance_registry__Called__ReturnsSingleton(self) -> None:
        """Test that get_provenance_registry returns the singleton."""
        registry = get_provenance_registry()

        self.assertIs(registry, ProvenanceRegistry())

    def test_register_preset__CustomPreset__AddsToRegistry(self) -> None:
        """Test that custom presets can be registered."""
        registry = get_provenance_registry()
        factory = lambda: ProvenanceFormatContext(show_paths=True)

        registry.register_preset("custom", factory, "Custom preset")

        self.assertIn("custom", registry)
        entry = registry.get_preset("custom")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "custom")
        self.assertEqual(entry.description, "Custom preset")
        self.assertFalse(entry.builtin)

    def test_register_preset__BuiltinNameConflict__RaisesValueError(self) -> None:
        """Test that overriding a built-in preset raises ValueError."""
        registry = get_provenance_registry()

        with self.assertRaises(ValueError) as ctx:
            registry.register_preset(
                "minimal",
                lambda: ProvenanceFormatContext(),
                "Override attempt",
            )

        self.assertIn("built-in preset", str(ctx.exception))
        self.assertIn("minimal", str(ctx.exception))

    def test_unregister_preset__CustomPreset__RemovesFromRegistry(self) -> None:
        """Test that custom presets can be unregistered."""
        registry = get_provenance_registry()
        registry.register_preset(
            "custom",
            lambda: ProvenanceFormatContext(),
            "Custom",
        )

        registry.unregister_preset("custom")

        self.assertNotIn("custom", registry)

    def test_unregister_preset__BuiltinPreset__RaisesValueError(self) -> None:
        """Test that unregistering a built-in preset raises ValueError."""
        registry = get_provenance_registry()

        with self.assertRaises(ValueError) as ctx:
            registry.unregister_preset("minimal")

        self.assertIn("built-in preset", str(ctx.exception))

    def test_unregister_preset__NonexistentPreset__RaisesKeyError(self) -> None:
        """Test that unregistering a nonexistent preset raises KeyError."""
        registry = get_provenance_registry()

        with self.assertRaises(KeyError) as ctx:
            registry.unregister_preset("nonexistent")

        self.assertIn("nonexistent", str(ctx.exception))

    def test_get_preset__ExistingPreset__ReturnsEntry(self) -> None:
        """Test that get_preset returns the entry for existing presets."""
        registry = get_provenance_registry()

        entry = registry.get_preset("minimal")

        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "minimal")
        self.assertTrue(entry.builtin)

    def test_get_preset__NonexistentPreset__ReturnsNone(self) -> None:
        """Test that get_preset returns None for nonexistent presets."""
        registry = get_provenance_registry()

        entry = registry.get_preset("nonexistent")

        self.assertIsNone(entry)

    def test_known_presets__ReturnsReadOnlyView(self) -> None:
        """Test that known_presets returns a read-only mapping."""
        registry = get_provenance_registry()

        presets = registry.known_presets

        self.assertIsInstance(presets, MappingProxyType)

    def test_clear_presets__RemovesCustomOnly__KeepsBuiltins(self) -> None:
        """Test that clear_presets removes custom presets but keeps built-ins."""
        registry = get_provenance_registry()
        registry.register_preset(
            "custom",
            lambda: ProvenanceFormatContext(),
            "Custom",
        )

        registry.clear_presets()

        self.assertNotIn("custom", registry)
        self.assertIn("minimal", registry)
        self.assertIn("full", registry)

    def test_contains__RegisteredPreset__ReturnsTrue(self) -> None:
        """Test that __contains__ returns True for registered presets."""
        registry = get_provenance_registry()

        self.assertIn("minimal", registry)

    def test_contains__UnregisteredPreset__ReturnsFalse(self) -> None:
        """Test that __contains__ returns False for unregistered presets."""
        registry = get_provenance_registry()

        self.assertNotIn("nonexistent", registry)


class ProvenanceBuiltinPresetsTests(TestCase):
    """Tests for built-in provenance presets."""

    def test_builtin_default__IsRegistered(self) -> None:
        """Test that default preset is registered."""
        registry = get_provenance_registry()

        self.assertIn("default", registry)
        entry = registry.get_preset("default")
        self.assertTrue(entry.builtin)

    def test_builtin_minimal__IsRegistered(self) -> None:
        """Test that minimal preset is registered."""
        registry = get_provenance_registry()

        self.assertIn("minimal", registry)
        entry = registry.get_preset("minimal")
        self.assertTrue(entry.builtin)

    def test_builtin_compact__IsRegistered(self) -> None:
        """Test that compact preset is registered."""
        registry = get_provenance_registry()

        self.assertIn("compact", registry)
        entry = registry.get_preset("compact")
        self.assertTrue(entry.builtin)

    def test_builtin_full__IsRegistered(self) -> None:
        """Test that full preset is registered."""
        registry = get_provenance_registry()

        self.assertIn("full", registry)
        entry = registry.get_preset("full")
        self.assertTrue(entry.builtin)

    def test_builtin_values__IsRegistered(self) -> None:
        """Test that values preset is registered."""
        registry = get_provenance_registry()

        self.assertIn("values", registry)
        entry = registry.get_preset("values")
        self.assertTrue(entry.builtin)

    def test_builtin_help__IsRegistered(self) -> None:
        """Test that help preset is registered."""
        registry = get_provenance_registry()

        self.assertIn("help", registry)
        entry = registry.get_preset("help")
        self.assertTrue(entry.builtin)

    def test_builtin_deprecations__IsRegistered(self) -> None:
        """Test that deprecations preset is registered."""
        registry = get_provenance_registry()

        self.assertIn("deprecations", registry)
        entry = registry.get_preset("deprecations")
        self.assertTrue(entry.builtin)

    def test_builtin_presets__FactoriesReturnValidContext(self) -> None:
        """Test that all built-in preset factories return valid contexts."""
        registry = get_provenance_registry()
        builtin_names = ["default", "minimal", "compact", "full", "values", "help", "deprecations"]

        for name in builtin_names:
            entry = registry.get_preset(name)
            with self.subTest(preset=name):
                ctx = entry.factory()
                self.assertIsInstance(ctx, ProvenanceFormatContext)


class ProvenanceLayoutEntryTests(TestCase):
    """Tests for ProvenanceLayoutEntry dataclass."""

    def test_ProvenanceLayoutEntry__Creation__StoresValues(self) -> None:
        """Test that entry stores all provided values."""
        factory = lambda: ProvenanceTreeLayout()
        entry = ProvenanceLayoutEntry(
            name="test",
            factory=factory,
            description="Test description",
            builtin=True,
        )

        self.assertEqual(entry.name, "test")
        self.assertEqual(entry.factory, factory)
        self.assertEqual(entry.description, "Test description")
        self.assertTrue(entry.builtin)

    def test_ProvenanceLayoutEntry__DefaultValues__HasCorrectDefaults(self) -> None:
        """Test that entry has correct default values."""
        entry = ProvenanceLayoutEntry(
            name="test",
            factory=lambda: ProvenanceTreeLayout(),
        )

        self.assertEqual(entry.description, "")
        self.assertFalse(entry.builtin)

    def test_ProvenanceLayoutEntry__Frozen__CannotModify(self) -> None:
        """Test that entry is immutable."""
        entry = ProvenanceLayoutEntry(
            name="test",
            factory=lambda: ProvenanceTreeLayout(),
        )

        with self.assertRaises(FrozenInstanceError):
            entry.name = "changed"  # type: ignore


class ProvenanceRegistryLayoutTests(TestCase):
    """Tests for ProvenanceRegistry layout methods."""

    def setUp(self) -> None:
        """Clear custom layouts before each test."""
        get_provenance_registry().clear_layouts()

    def tearDown(self) -> None:
        """Clear custom layouts after each test."""
        get_provenance_registry().clear_layouts()

    def test_register_layout__CustomLayout__AddsToRegistry(self) -> None:
        """Test that custom layouts can be registered."""
        registry = get_provenance_registry()
        factory = lambda: ProvenanceTreeLayout()

        registry.register_layout("custom", factory, "Custom layout")

        self.assertTrue(registry.has_layout("custom"))
        entry = registry.get_layout("custom")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "custom")
        self.assertEqual(entry.description, "Custom layout")
        self.assertFalse(entry.builtin)

    def test_register_layout__BuiltinNameConflict__RaisesValueError(self) -> None:
        """Test that overriding a built-in layout raises ValueError."""
        registry = get_provenance_registry()

        with self.assertRaises(ValueError) as ctx:
            registry.register_layout(
                "tree",
                lambda: ProvenanceTreeLayout(),
                "Override attempt",
            )

        self.assertIn("built-in layout", str(ctx.exception))
        self.assertIn("tree", str(ctx.exception))

    def test_unregister_layout__CustomLayout__RemovesFromRegistry(self) -> None:
        """Test that custom layouts can be unregistered."""
        registry = get_provenance_registry()
        registry.register_layout(
            "custom",
            lambda: ProvenanceTreeLayout(),
            "Custom",
        )

        registry.unregister_layout("custom")

        self.assertFalse(registry.has_layout("custom"))

    def test_unregister_layout__BuiltinLayout__RaisesValueError(self) -> None:
        """Test that unregistering a built-in layout raises ValueError."""
        registry = get_provenance_registry()

        with self.assertRaises(ValueError) as ctx:
            registry.unregister_layout("tree")

        self.assertIn("built-in layout", str(ctx.exception))

    def test_unregister_layout__NonexistentLayout__RaisesKeyError(self) -> None:
        """Test that unregistering a nonexistent layout raises KeyError."""
        registry = get_provenance_registry()

        with self.assertRaises(KeyError) as ctx:
            registry.unregister_layout("nonexistent")

        self.assertIn("nonexistent", str(ctx.exception))

    def test_get_layout__ExistingLayout__ReturnsEntry(self) -> None:
        """Test that get_layout returns the entry for existing layouts."""
        registry = get_provenance_registry()

        entry = registry.get_layout("tree")

        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "tree")
        self.assertTrue(entry.builtin)

    def test_get_layout__NonexistentLayout__ReturnsNone(self) -> None:
        """Test that get_layout returns None for nonexistent layouts."""
        registry = get_provenance_registry()

        entry = registry.get_layout("nonexistent")

        self.assertIsNone(entry)

    def test_known_layouts__ReturnsReadOnlyView(self) -> None:
        """Test that known_layouts returns a read-only mapping."""
        registry = get_provenance_registry()

        layouts = registry.known_layouts

        self.assertIsInstance(layouts, MappingProxyType)

    def test_has_layout__RegisteredLayout__ReturnsTrue(self) -> None:
        """Test that has_layout returns True for registered layouts."""
        registry = get_provenance_registry()

        self.assertTrue(registry.has_layout("tree"))

    def test_has_layout__UnregisteredLayout__ReturnsFalse(self) -> None:
        """Test that has_layout returns False for unregistered layouts."""
        registry = get_provenance_registry()

        self.assertFalse(registry.has_layout("nonexistent"))

    def test_clear_layouts__RemovesCustomOnly__KeepsBuiltins(self) -> None:
        """Test that clear_layouts removes custom layouts but keeps built-ins."""
        registry = get_provenance_registry()
        registry.register_layout(
            "custom",
            lambda: ProvenanceTreeLayout(),
            "Custom",
        )

        registry.clear_layouts()

        self.assertFalse(registry.has_layout("custom"))
        self.assertTrue(registry.has_layout("tree"))
        self.assertTrue(registry.has_layout("flat"))


class ProvenanceBuiltinLayoutsTests(TestCase):
    """Tests for built-in provenance layouts."""

    def test_builtin_tree__IsRegistered(self) -> None:
        """Test that tree layout is registered."""
        registry = get_provenance_registry()

        self.assertTrue(registry.has_layout("tree"))
        entry = registry.get_layout("tree")
        self.assertTrue(entry.builtin)

    def test_builtin_flat__IsRegistered(self) -> None:
        """Test that flat layout is registered."""
        registry = get_provenance_registry()

        self.assertTrue(registry.has_layout("flat"))
        entry = registry.get_layout("flat")
        self.assertTrue(entry.builtin)

    def test_builtin_markdown__IsRegistered(self) -> None:
        """Test that markdown layout is registered."""
        registry = get_provenance_registry()

        self.assertTrue(registry.has_layout("markdown"))
        entry = registry.get_layout("markdown")
        self.assertTrue(entry.builtin)

    def test_builtin_layouts__FactoriesReturnValidLayout(self) -> None:
        """Test that all built-in layout factories return valid layouts."""
        registry = get_provenance_registry()
        builtin_names = ["tree", "flat", "markdown"]

        for name in builtin_names:
            entry = registry.get_layout(name)
            with self.subTest(layout=name):
                layout = entry.factory()
                self.assertIsInstance(layout, ProvenanceLayout)
