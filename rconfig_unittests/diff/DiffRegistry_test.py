"""Tests for DiffRegistry and preset/layout management."""

from dataclasses import FrozenInstanceError
from types import MappingProxyType
from unittest import TestCase

from rconfig.diff.formatting import (
    DiffFlatLayout,
    DiffFormatContext,
    DiffLayout,
    DiffLayoutEntry,
    DiffPresetEntry,
    DiffRegistry,
    get_diff_registry,
)


class DiffPresetEntryTests(TestCase):
    """Tests for DiffPresetEntry dataclass."""

    def test_DiffPresetEntry__Creation__StoresValues(self) -> None:
        """Test that entry stores all provided values."""
        factory = lambda: DiffFormatContext()
        entry = DiffPresetEntry(
            name="test",
            factory=factory,
            description="Test description",
            builtin=True,
        )

        self.assertEqual(entry.name, "test")
        self.assertEqual(entry.factory, factory)
        self.assertEqual(entry.description, "Test description")
        self.assertTrue(entry.builtin)

    def test_DiffPresetEntry__DefaultValues__HasCorrectDefaults(self) -> None:
        """Test that entry has correct default values."""
        entry = DiffPresetEntry(
            name="test",
            factory=lambda: DiffFormatContext(),
        )

        self.assertEqual(entry.description, "")
        self.assertFalse(entry.builtin)

    def test_DiffPresetEntry__Frozen__CannotModify(self) -> None:
        """Test that entry is immutable."""
        entry = DiffPresetEntry(
            name="test",
            factory=lambda: DiffFormatContext(),
        )

        with self.assertRaises(FrozenInstanceError):
            entry.name = "changed"  # type: ignore


class DiffRegistryTests(TestCase):
    """Tests for DiffRegistry singleton."""

    def setUp(self) -> None:
        """Clear custom presets before each test."""
        get_diff_registry().clear_presets()

    def tearDown(self) -> None:
        """Clear custom presets after each test."""
        get_diff_registry().clear_presets()

    def test_DiffRegistry__Singleton__ReturnsSameInstance(self) -> None:
        """Test that registry is a singleton."""
        registry1 = DiffRegistry()
        registry2 = DiffRegistry()

        self.assertIs(registry1, registry2)

    def test_get_diff_registry__Called__ReturnsSingleton(self) -> None:
        """Test that get_diff_registry returns the singleton."""
        registry = get_diff_registry()

        self.assertIs(registry, DiffRegistry())

    def test_register_preset__CustomPreset__AddsToRegistry(self) -> None:
        """Test that custom presets can be registered."""
        registry = get_diff_registry()
        factory = lambda: DiffFormatContext(show_added=True)

        registry.register_preset("custom", factory, "Custom preset")

        self.assertIn("custom", registry)
        entry = registry.get_preset("custom")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "custom")
        self.assertEqual(entry.description, "Custom preset")
        self.assertFalse(entry.builtin)

    def test_register_preset__BuiltinNameConflict__RaisesValueError(self) -> None:
        """Test that overriding a built-in preset raises ValueError."""
        registry = get_diff_registry()

        with self.assertRaises(ValueError) as ctx:
            registry.register_preset(
                "changes_only",
                lambda: DiffFormatContext(),
                "Override attempt",
            )

        self.assertIn("built-in preset", str(ctx.exception))
        self.assertIn("changes_only", str(ctx.exception))

    def test_unregister_preset__CustomPreset__RemovesFromRegistry(self) -> None:
        """Test that custom presets can be unregistered."""
        registry = get_diff_registry()
        registry.register_preset(
            "custom",
            lambda: DiffFormatContext(),
            "Custom",
        )

        registry.unregister_preset("custom")

        self.assertNotIn("custom", registry)

    def test_unregister_preset__BuiltinPreset__RaisesValueError(self) -> None:
        """Test that unregistering a built-in preset raises ValueError."""
        registry = get_diff_registry()

        with self.assertRaises(ValueError) as ctx:
            registry.unregister_preset("changes_only")

        self.assertIn("built-in preset", str(ctx.exception))

    def test_unregister_preset__NonexistentPreset__RaisesKeyError(self) -> None:
        """Test that unregistering a nonexistent preset raises KeyError."""
        registry = get_diff_registry()

        with self.assertRaises(KeyError) as ctx:
            registry.unregister_preset("nonexistent")

        self.assertIn("nonexistent", str(ctx.exception))

    def test_get_preset__ExistingPreset__ReturnsEntry(self) -> None:
        """Test that get_preset returns the entry for existing presets."""
        registry = get_diff_registry()

        entry = registry.get_preset("changes_only")

        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "changes_only")
        self.assertTrue(entry.builtin)

    def test_get_preset__NonexistentPreset__ReturnsNone(self) -> None:
        """Test that get_preset returns None for nonexistent presets."""
        registry = get_diff_registry()

        entry = registry.get_preset("nonexistent")

        self.assertIsNone(entry)

    def test_known_presets__ReturnsReadOnlyView(self) -> None:
        """Test that known_presets returns a read-only mapping."""
        registry = get_diff_registry()

        presets = registry.known_presets

        self.assertIsInstance(presets, MappingProxyType)

    def test_clear_presets__RemovesCustomOnly__KeepsBuiltins(self) -> None:
        """Test that clear_presets removes custom presets but keeps built-ins."""
        registry = get_diff_registry()
        registry.register_preset(
            "custom",
            lambda: DiffFormatContext(),
            "Custom",
        )

        registry.clear_presets()

        self.assertNotIn("custom", registry)
        self.assertIn("changes_only", registry)
        self.assertIn("full", registry)

    def test_contains__RegisteredPreset__ReturnsTrue(self) -> None:
        """Test that __contains__ returns True for registered presets."""
        registry = get_diff_registry()

        self.assertIn("changes_only", registry)

    def test_contains__UnregisteredPreset__ReturnsFalse(self) -> None:
        """Test that __contains__ returns False for unregistered presets."""
        registry = get_diff_registry()

        self.assertNotIn("nonexistent", registry)


class DiffBuiltinPresetsTests(TestCase):
    """Tests for built-in diff presets."""

    def test_builtin_default__IsRegistered(self) -> None:
        """Test that default preset is registered."""
        registry = get_diff_registry()

        self.assertIn("default", registry)
        entry = registry.get_preset("default")
        self.assertTrue(entry.builtin)

    def test_builtin_changes_only__IsRegistered(self) -> None:
        """Test that changes_only preset is registered."""
        registry = get_diff_registry()

        self.assertIn("changes_only", registry)
        entry = registry.get_preset("changes_only")
        self.assertTrue(entry.builtin)

    def test_builtin_with_context__IsRegistered(self) -> None:
        """Test that with_context preset is registered."""
        registry = get_diff_registry()

        self.assertIn("with_context", registry)
        entry = registry.get_preset("with_context")
        self.assertTrue(entry.builtin)

    def test_builtin_full__IsRegistered(self) -> None:
        """Test that full preset is registered."""
        registry = get_diff_registry()

        self.assertIn("full", registry)
        entry = registry.get_preset("full")
        self.assertTrue(entry.builtin)

    def test_builtin_summary__IsRegistered(self) -> None:
        """Test that summary preset is registered."""
        registry = get_diff_registry()

        self.assertIn("summary", registry)
        entry = registry.get_preset("summary")
        self.assertTrue(entry.builtin)

    def test_builtin_presets__FactoriesReturnValidContext(self) -> None:
        """Test that all built-in preset factories return valid contexts."""
        registry = get_diff_registry()
        builtin_names = ["default", "changes_only", "with_context", "full", "summary"]

        for name in builtin_names:
            entry = registry.get_preset(name)
            with self.subTest(preset=name):
                ctx = entry.factory()
                self.assertIsInstance(ctx, DiffFormatContext)


class DiffLayoutEntryTests(TestCase):
    """Tests for DiffLayoutEntry dataclass."""

    def test_DiffLayoutEntry__Creation__StoresValues(self) -> None:
        """Test that entry stores all provided values."""
        factory = lambda: DiffFlatLayout()
        entry = DiffLayoutEntry(
            name="test",
            factory=factory,
            description="Test description",
            builtin=True,
        )

        self.assertEqual(entry.name, "test")
        self.assertEqual(entry.factory, factory)
        self.assertEqual(entry.description, "Test description")
        self.assertTrue(entry.builtin)

    def test_DiffLayoutEntry__DefaultValues__HasCorrectDefaults(self) -> None:
        """Test that entry has correct default values."""
        entry = DiffLayoutEntry(
            name="test",
            factory=lambda: DiffFlatLayout(),
        )

        self.assertEqual(entry.description, "")
        self.assertFalse(entry.builtin)

    def test_DiffLayoutEntry__Frozen__CannotModify(self) -> None:
        """Test that entry is immutable."""
        entry = DiffLayoutEntry(
            name="test",
            factory=lambda: DiffFlatLayout(),
        )

        with self.assertRaises(FrozenInstanceError):
            entry.name = "changed"  # type: ignore


class DiffRegistryLayoutTests(TestCase):
    """Tests for DiffRegistry layout methods."""

    def setUp(self) -> None:
        """Clear custom layouts before each test."""
        get_diff_registry().clear_layouts()

    def tearDown(self) -> None:
        """Clear custom layouts after each test."""
        get_diff_registry().clear_layouts()

    def test_register_layout__CustomLayout__AddsToRegistry(self) -> None:
        """Test that custom layouts can be registered."""
        registry = get_diff_registry()
        factory = lambda: DiffFlatLayout()

        registry.register_layout("custom", factory, "Custom layout")

        self.assertTrue(registry.has_layout("custom"))
        entry = registry.get_layout("custom")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "custom")
        self.assertEqual(entry.description, "Custom layout")
        self.assertFalse(entry.builtin)

    def test_register_layout__BuiltinNameConflict__RaisesValueError(self) -> None:
        """Test that overriding a built-in layout raises ValueError."""
        registry = get_diff_registry()

        with self.assertRaises(ValueError) as ctx:
            registry.register_layout(
                "flat",
                lambda: DiffFlatLayout(),
                "Override attempt",
            )

        self.assertIn("built-in layout", str(ctx.exception))
        self.assertIn("flat", str(ctx.exception))

    def test_unregister_layout__CustomLayout__RemovesFromRegistry(self) -> None:
        """Test that custom layouts can be unregistered."""
        registry = get_diff_registry()
        registry.register_layout(
            "custom",
            lambda: DiffFlatLayout(),
            "Custom",
        )

        registry.unregister_layout("custom")

        self.assertFalse(registry.has_layout("custom"))

    def test_unregister_layout__BuiltinLayout__RaisesValueError(self) -> None:
        """Test that unregistering a built-in layout raises ValueError."""
        registry = get_diff_registry()

        with self.assertRaises(ValueError) as ctx:
            registry.unregister_layout("flat")

        self.assertIn("built-in layout", str(ctx.exception))

    def test_unregister_layout__NonexistentLayout__RaisesKeyError(self) -> None:
        """Test that unregistering a nonexistent layout raises KeyError."""
        registry = get_diff_registry()

        with self.assertRaises(KeyError) as ctx:
            registry.unregister_layout("nonexistent")

        self.assertIn("nonexistent", str(ctx.exception))

    def test_get_layout__ExistingLayout__ReturnsEntry(self) -> None:
        """Test that get_layout returns the entry for existing layouts."""
        registry = get_diff_registry()

        entry = registry.get_layout("flat")

        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "flat")
        self.assertTrue(entry.builtin)

    def test_get_layout__NonexistentLayout__ReturnsNone(self) -> None:
        """Test that get_layout returns None for nonexistent layouts."""
        registry = get_diff_registry()

        entry = registry.get_layout("nonexistent")

        self.assertIsNone(entry)

    def test_known_layouts__ReturnsReadOnlyView(self) -> None:
        """Test that known_layouts returns a read-only mapping."""
        registry = get_diff_registry()

        layouts = registry.known_layouts

        self.assertIsInstance(layouts, MappingProxyType)

    def test_has_layout__RegisteredLayout__ReturnsTrue(self) -> None:
        """Test that has_layout returns True for registered layouts."""
        registry = get_diff_registry()

        self.assertTrue(registry.has_layout("flat"))

    def test_has_layout__UnregisteredLayout__ReturnsFalse(self) -> None:
        """Test that has_layout returns False for unregistered layouts."""
        registry = get_diff_registry()

        self.assertFalse(registry.has_layout("nonexistent"))

    def test_clear_layouts__RemovesCustomOnly__KeepsBuiltins(self) -> None:
        """Test that clear_layouts removes custom layouts but keeps built-ins."""
        registry = get_diff_registry()
        registry.register_layout(
            "custom",
            lambda: DiffFlatLayout(),
            "Custom",
        )

        registry.clear_layouts()

        self.assertFalse(registry.has_layout("custom"))
        self.assertTrue(registry.has_layout("flat"))
        self.assertTrue(registry.has_layout("tree"))


class DiffBuiltinLayoutsTests(TestCase):
    """Tests for built-in diff layouts."""

    def test_builtin_flat__IsRegistered(self) -> None:
        """Test that flat layout is registered."""
        registry = get_diff_registry()

        self.assertTrue(registry.has_layout("flat"))
        entry = registry.get_layout("flat")
        self.assertTrue(entry.builtin)

    def test_builtin_tree__IsRegistered(self) -> None:
        """Test that tree layout is registered."""
        registry = get_diff_registry()

        self.assertTrue(registry.has_layout("tree"))
        entry = registry.get_layout("tree")
        self.assertTrue(entry.builtin)

    def test_builtin_markdown__IsRegistered(self) -> None:
        """Test that markdown layout is registered."""
        registry = get_diff_registry()

        self.assertTrue(registry.has_layout("markdown"))
        entry = registry.get_layout("markdown")
        self.assertTrue(entry.builtin)

    def test_builtin_layouts__FactoriesReturnValidLayout(self) -> None:
        """Test that all built-in layout factories return valid layouts."""
        registry = get_diff_registry()
        builtin_names = ["flat", "tree", "markdown"]

        for name in builtin_names:
            entry = registry.get_layout(name)
            with self.subTest(layout=name):
                layout = entry.factory()
                self.assertIsInstance(layout, DiffLayout)
