"""Tests for DiffRegistry and preset management."""

from dataclasses import FrozenInstanceError
from types import MappingProxyType
from unittest import TestCase

from rconfig.diff.formatting import (
    DiffFormatContext,
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
        get_diff_registry().clear()

    def tearDown(self) -> None:
        """Clear custom presets after each test."""
        get_diff_registry().clear()

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

    def test_clear__RemovesCustomOnly__KeepsBuiltins(self) -> None:
        """Test that clear removes custom presets but keeps built-ins."""
        registry = get_diff_registry()
        registry.register_preset(
            "custom",
            lambda: DiffFormatContext(),
            "Custom",
        )

        registry.clear()

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
