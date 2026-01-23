"""Tests for FormattingRegistry base class and generic entry dataclasses."""

from dataclasses import FrozenInstanceError
from types import MappingProxyType
from unittest import TestCase

from rconfig._internal.formatting_registry import (
    FormattingRegistry,
    LayoutEntry,
    PresetEntry,
)


# Concrete test subclass for testing the ABC
class _TestRegistry(FormattingRegistry[str, str]):
    pass


class PresetEntryTests(TestCase):
    """Tests for PresetEntry generic dataclass."""

    def test_PresetEntry__Creation__StoresValues(self) -> None:
        """Test that entry stores all provided values."""
        # Arrange
        factory = lambda: "context"

        # Act
        entry = PresetEntry(
            name="test",
            factory=factory,
            description="A test preset",
            builtin=True,
        )

        # Assert
        self.assertEqual(entry.name, "test")
        self.assertEqual(entry.factory, factory)
        self.assertEqual(entry.description, "A test preset")
        self.assertTrue(entry.builtin)

    def test_PresetEntry__DefaultValues__HasCorrectDefaults(self) -> None:
        """Test that entry has correct default values."""
        # Act
        entry = PresetEntry(name="test", factory=lambda: "ctx")

        # Assert
        self.assertEqual(entry.description, "")
        self.assertFalse(entry.builtin)

    def test_PresetEntry__Frozen__CannotModify(self) -> None:
        """Test that entry is immutable."""
        # Arrange
        entry = PresetEntry(name="test", factory=lambda: "ctx")

        # Act & Assert
        with self.assertRaises(FrozenInstanceError):
            entry.name = "changed"  # type: ignore


class LayoutEntryTests(TestCase):
    """Tests for LayoutEntry generic dataclass."""

    def test_LayoutEntry__Creation__StoresValues(self) -> None:
        """Test that entry stores all provided values."""
        # Arrange
        factory = lambda: "layout"

        # Act
        entry = LayoutEntry(
            name="tree",
            factory=factory,
            description="Tree layout",
            builtin=True,
        )

        # Assert
        self.assertEqual(entry.name, "tree")
        self.assertEqual(entry.factory, factory)
        self.assertEqual(entry.description, "Tree layout")
        self.assertTrue(entry.builtin)

    def test_LayoutEntry__DefaultValues__HasCorrectDefaults(self) -> None:
        """Test that entry has correct default values."""
        # Act
        entry = LayoutEntry(name="flat", factory=lambda: "layout")

        # Assert
        self.assertEqual(entry.description, "")
        self.assertFalse(entry.builtin)

    def test_LayoutEntry__Frozen__CannotModify(self) -> None:
        """Test that entry is immutable."""
        # Arrange
        entry = LayoutEntry(name="flat", factory=lambda: "layout")

        # Act & Assert
        with self.assertRaises(FrozenInstanceError):
            entry.name = "changed"  # type: ignore


class FormattingRegistryPresetTests(TestCase):
    """Tests for FormattingRegistry preset operations."""

    def setUp(self) -> None:
        """Create a fresh registry for each test."""
        self.registry = _TestRegistry()

    def test_register_preset__NewPreset__AddsToRegistry(self) -> None:
        """Test that a new preset is added to the registry."""
        # Arrange
        factory = lambda: "context"

        # Act
        self.registry.register_preset("custom", factory, "Custom preset")

        # Assert
        self.assertIn("custom", self.registry)
        entry = self.registry.get_preset("custom")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "custom")
        self.assertEqual(entry.description, "Custom preset")
        self.assertFalse(entry.builtin)

    def test_register_preset__BuiltinPreset__MarkedAsBuiltin(self) -> None:
        """Test that builtin presets are marked correctly."""
        # Act
        self.registry.register_preset("default", lambda: "ctx", builtin=True)

        # Assert
        entry = self.registry.get_preset("default")
        self.assertTrue(entry.builtin)

    def test_register_preset__OverrideBuiltin__RaisesValueError(self) -> None:
        """Test that overriding a built-in preset raises ValueError."""
        # Arrange
        self.registry.register_preset("default", lambda: "ctx", builtin=True)

        # Act & Assert
        with self.assertRaises(ValueError) as ctx:
            self.registry.register_preset("default", lambda: "other")
        self.assertIn("built-in", str(ctx.exception))

    def test_register_preset__OverrideCustom__Replaces(self) -> None:
        """Test that overriding a custom preset replaces it."""
        # Arrange
        self.registry.register_preset("custom", lambda: "first")

        # Act
        self.registry.register_preset("custom", lambda: "second", description="v2")

        # Assert
        entry = self.registry.get_preset("custom")
        self.assertEqual(entry.description, "v2")

    def test_unregister_preset__ExistingCustom__RemovesFromRegistry(self) -> None:
        """Test that unregistering a custom preset removes it."""
        # Arrange
        self.registry.register_preset("custom", lambda: "ctx")

        # Act
        self.registry.unregister_preset("custom")

        # Assert
        self.assertNotIn("custom", self.registry)

    def test_unregister_preset__NonExistent__RaisesKeyError(self) -> None:
        """Test that unregistering a non-existent preset raises KeyError."""
        # Act & Assert
        with self.assertRaises(KeyError):
            self.registry.unregister_preset("nonexistent")

    def test_unregister_preset__BuiltinPreset__RaisesValueError(self) -> None:
        """Test that unregistering a built-in preset raises ValueError."""
        # Arrange
        self.registry.register_preset("default", lambda: "ctx", builtin=True)

        # Act & Assert
        with self.assertRaises(ValueError) as ctx:
            self.registry.unregister_preset("default")
        self.assertIn("built-in", str(ctx.exception))

    def test_get_preset__Existing__ReturnsEntry(self) -> None:
        """Test that get_preset returns the entry for existing presets."""
        # Arrange
        self.registry.register_preset("test", lambda: "ctx")

        # Act
        entry = self.registry.get_preset("test")

        # Assert
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "test")

    def test_get_preset__NonExistent__ReturnsNone(self) -> None:
        """Test that get_preset returns None for non-existent presets."""
        # Act & Assert
        self.assertIsNone(self.registry.get_preset("nonexistent"))

    def test_known_presets__MultipleRegistered__ReturnsMappingProxy(self) -> None:
        """Test that known_presets returns a MappingProxyType."""
        # Arrange
        self.registry.register_preset("a", lambda: "ctx")
        self.registry.register_preset("b", lambda: "ctx")

        # Act
        result = self.registry.known_presets

        # Assert
        self.assertIsInstance(result, MappingProxyType)
        self.assertEqual(len(result), 2)
        self.assertIn("a", result)
        self.assertIn("b", result)

    def test_contains__RegisteredPreset__ReturnsTrue(self) -> None:
        """Test that __contains__ returns True for registered presets."""
        # Arrange
        self.registry.register_preset("test", lambda: "ctx")

        # Act & Assert
        self.assertIn("test", self.registry)

    def test_contains__UnregisteredPreset__ReturnsFalse(self) -> None:
        """Test that __contains__ returns False for unregistered presets."""
        # Act & Assert
        self.assertNotIn("test", self.registry)

    def test_clear_presets__MixedEntries__KeepsBuiltins(self) -> None:
        """Test that clear_presets removes custom but keeps built-in presets."""
        # Arrange
        self.registry.register_preset("builtin1", lambda: "ctx", builtin=True)
        self.registry.register_preset("custom1", lambda: "ctx")
        self.registry.register_preset("custom2", lambda: "ctx")

        # Act
        self.registry.clear_presets()

        # Assert
        self.assertIn("builtin1", self.registry)
        self.assertNotIn("custom1", self.registry)
        self.assertNotIn("custom2", self.registry)


class FormattingRegistryLayoutTests(TestCase):
    """Tests for FormattingRegistry layout operations."""

    def setUp(self) -> None:
        """Create a fresh registry for each test."""
        self.registry = _TestRegistry()

    def test_register_layout__NewLayout__AddsToRegistry(self) -> None:
        """Test that a new layout is added to the registry."""
        # Arrange
        factory = lambda: "tree_layout"

        # Act
        self.registry.register_layout("tree", factory, "Tree layout")

        # Assert
        self.assertTrue(self.registry.has_layout("tree"))
        entry = self.registry.get_layout("tree")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "tree")
        self.assertEqual(entry.description, "Tree layout")

    def test_register_layout__BuiltinLayout__MarkedAsBuiltin(self) -> None:
        """Test that builtin layouts are marked correctly."""
        # Act
        self.registry.register_layout("tree", lambda: "layout", builtin=True)

        # Assert
        entry = self.registry.get_layout("tree")
        self.assertTrue(entry.builtin)

    def test_register_layout__OverrideBuiltin__RaisesValueError(self) -> None:
        """Test that overriding a built-in layout raises ValueError."""
        # Arrange
        self.registry.register_layout("tree", lambda: "layout", builtin=True)

        # Act & Assert
        with self.assertRaises(ValueError) as ctx:
            self.registry.register_layout("tree", lambda: "other")
        self.assertIn("built-in", str(ctx.exception))

    def test_register_layout__OverrideCustom__Replaces(self) -> None:
        """Test that overriding a custom layout replaces it."""
        # Arrange
        self.registry.register_layout("custom", lambda: "first")

        # Act
        self.registry.register_layout("custom", lambda: "second", description="v2")

        # Assert
        entry = self.registry.get_layout("custom")
        self.assertEqual(entry.description, "v2")

    def test_unregister_layout__ExistingCustom__RemovesFromRegistry(self) -> None:
        """Test that unregistering a custom layout removes it."""
        # Arrange
        self.registry.register_layout("custom", lambda: "layout")

        # Act
        self.registry.unregister_layout("custom")

        # Assert
        self.assertFalse(self.registry.has_layout("custom"))

    def test_unregister_layout__NonExistent__RaisesKeyError(self) -> None:
        """Test that unregistering a non-existent layout raises KeyError."""
        # Act & Assert
        with self.assertRaises(KeyError):
            self.registry.unregister_layout("nonexistent")

    def test_unregister_layout__BuiltinLayout__RaisesValueError(self) -> None:
        """Test that unregistering a built-in layout raises ValueError."""
        # Arrange
        self.registry.register_layout("tree", lambda: "layout", builtin=True)

        # Act & Assert
        with self.assertRaises(ValueError) as ctx:
            self.registry.unregister_layout("tree")
        self.assertIn("built-in", str(ctx.exception))

    def test_get_layout__Existing__ReturnsEntry(self) -> None:
        """Test that get_layout returns the entry for existing layouts."""
        # Arrange
        self.registry.register_layout("flat", lambda: "layout")

        # Act
        entry = self.registry.get_layout("flat")

        # Assert
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "flat")

    def test_get_layout__NonExistent__ReturnsNone(self) -> None:
        """Test that get_layout returns None for non-existent layouts."""
        # Act & Assert
        self.assertIsNone(self.registry.get_layout("nonexistent"))

    def test_known_layouts__MultipleRegistered__ReturnsMappingProxy(self) -> None:
        """Test that known_layouts returns a MappingProxyType."""
        # Arrange
        self.registry.register_layout("tree", lambda: "layout")
        self.registry.register_layout("flat", lambda: "layout")

        # Act
        result = self.registry.known_layouts

        # Assert
        self.assertIsInstance(result, MappingProxyType)
        self.assertEqual(len(result), 2)

    def test_has_layout__RegisteredLayout__ReturnsTrue(self) -> None:
        """Test that has_layout returns True for registered layouts."""
        # Arrange
        self.registry.register_layout("tree", lambda: "layout")

        # Act & Assert
        self.assertTrue(self.registry.has_layout("tree"))

    def test_has_layout__UnregisteredLayout__ReturnsFalse(self) -> None:
        """Test that has_layout returns False for unregistered layouts."""
        # Act & Assert
        self.assertFalse(self.registry.has_layout("nonexistent"))

    def test_clear_layouts__MixedEntries__KeepsBuiltins(self) -> None:
        """Test that clear_layouts removes custom but keeps built-in layouts."""
        # Arrange
        self.registry.register_layout("builtin1", lambda: "layout", builtin=True)
        self.registry.register_layout("custom1", lambda: "layout")
        self.registry.register_layout("custom2", lambda: "layout")

        # Act
        self.registry.clear_layouts()

        # Assert
        self.assertTrue(self.registry.has_layout("builtin1"))
        self.assertFalse(self.registry.has_layout("custom1"))
        self.assertFalse(self.registry.has_layout("custom2"))


class FormattingRegistryIsolationTests(TestCase):
    """Tests for preset/layout isolation within the registry."""

    def setUp(self) -> None:
        """Create a fresh registry for each test."""
        self.registry = _TestRegistry()

    def test_contains__LayoutName__DoesNotMatchPreset(self) -> None:
        """Test that __contains__ only checks presets, not layouts."""
        # Arrange
        self.registry.register_layout("tree", lambda: "layout")

        # Act & Assert
        self.assertNotIn("tree", self.registry)

    def test_has_layout__PresetName__DoesNotMatchLayout(self) -> None:
        """Test that has_layout only checks layouts, not presets."""
        # Arrange
        self.registry.register_preset("compact", lambda: "ctx")

        # Act & Assert
        self.assertFalse(self.registry.has_layout("compact"))

    def test_clear_presets__LayoutsExist__LayoutsUnaffected(self) -> None:
        """Test that clearing presets does not affect layouts."""
        # Arrange
        self.registry.register_preset("custom_preset", lambda: "ctx")
        self.registry.register_layout("custom_layout", lambda: "layout")

        # Act
        self.registry.clear_presets()

        # Assert
        self.assertTrue(self.registry.has_layout("custom_layout"))

    def test_clear_layouts__PresetsExist__PresetsUnaffected(self) -> None:
        """Test that clearing layouts does not affect presets."""
        # Arrange
        self.registry.register_preset("custom_preset", lambda: "ctx")
        self.registry.register_layout("custom_layout", lambda: "layout")

        # Act
        self.registry.clear_layouts()

        # Assert
        self.assertIn("custom_preset", self.registry)
