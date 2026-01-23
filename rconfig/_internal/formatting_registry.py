"""Base class for formatting registries (provenance, diff).

Provides the common dual-entry (preset + layout) registry pattern
with thread safety, builtin protection, and read-only views.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Generic, TypeVar

TContext = TypeVar("TContext")
TLayout = TypeVar("TLayout")


@dataclass(frozen=True, kw_only=True)
class PresetEntry(Generic[TContext]):
    """Immutable entry for a registered format preset.

    :param name: Unique identifier for the preset.
    :param factory: Callable returning a format context with preset settings.
    :param description: Human-readable description.
    :param builtin: True if this is a built-in preset.
    """

    name: str
    factory: Callable[[], TContext]
    description: str = ""
    builtin: bool = False


@dataclass(frozen=True, kw_only=True)
class LayoutEntry(Generic[TLayout]):
    """Immutable entry for a registered layout.

    :param name: Unique identifier for the layout.
    :param factory: Callable returning a layout instance.
    :param description: Human-readable description.
    :param builtin: True if this is a built-in layout.
    """

    name: str
    factory: Callable[[], TLayout]
    description: str = ""
    builtin: bool = False


class FormattingRegistry(Generic[TContext, TLayout]):
    """Thread-safe base class for formatting registries with dual-entry pattern.

    Subclasses provide the specific context type (e.g., ProvenanceFormatContext)
    and layout type (e.g., ProvenanceLayout) via generics.

    Thread-safe: All mutation operations are protected by an internal RLock.
    """

    def __init__(self) -> None:
        """Initialize the registry with empty preset and layout dictionaries."""
        self._presets: dict[str, PresetEntry[TContext]] = {}
        self._layouts: dict[str, LayoutEntry[TLayout]] = {}
        self._lock = threading.RLock()

    # --- Preset Methods ---

    @property
    def known_presets(self) -> MappingProxyType[str, PresetEntry[TContext]]:
        """Read-only view of all registered presets."""
        return MappingProxyType(self._presets)

    def register_preset(
        self,
        name: str,
        factory: Callable[[], TContext],
        description: str = "",
        *,
        builtin: bool = False,
    ) -> None:
        """Register a format preset.

        :param name: Preset name.
        :param factory: Callable returning a format context.
        :param description: Human-readable description.
        :param builtin: True if this is a built-in preset (internal use).
        :raises ValueError: If name conflicts with a built-in preset.
        """
        entry = PresetEntry(
            name=name,
            factory=factory,
            description=description,
            builtin=builtin,
        )

        with self._lock:
            if name in self._presets and self._presets[name].builtin and not builtin:
                raise ValueError(
                    f"Cannot override built-in preset '{name}'. Use a different name."
                )
            self._presets[name] = entry

    def unregister_preset(self, name: str) -> None:
        """Unregister a custom preset.

        :param name: Preset name to unregister.
        :raises KeyError: If preset is not registered.
        :raises ValueError: If trying to unregister a built-in preset.
        """
        with self._lock:
            if name not in self._presets:
                raise KeyError(f"Preset '{name}' is not registered")
            if self._presets[name].builtin:
                raise ValueError(f"Cannot unregister built-in preset '{name}'")
            del self._presets[name]

    def get_preset(self, name: str) -> PresetEntry[TContext] | None:
        """Get a preset entry by name.

        :param name: Preset name.
        :return: Preset entry or None if not found.
        """
        return self._presets.get(name)

    def __contains__(self, name: str) -> bool:
        """Check if a preset is registered.

        :param name: Preset name.
        :return: True if preset is registered.
        """
        with self._lock:
            return name in self._presets

    def clear_presets(self) -> None:
        """Clear all custom presets, keeping built-ins.

        Primarily for testing.
        """
        with self._lock:
            self._presets = {k: v for k, v in self._presets.items() if v.builtin}

    # --- Layout Methods ---

    @property
    def known_layouts(self) -> MappingProxyType[str, LayoutEntry[TLayout]]:
        """Read-only view of all registered layouts."""
        return MappingProxyType(self._layouts)

    def register_layout(
        self,
        name: str,
        factory: Callable[[], TLayout],
        description: str = "",
        *,
        builtin: bool = False,
    ) -> None:
        """Register a format layout.

        :param name: Layout name.
        :param factory: Callable returning a layout instance.
        :param description: Human-readable description.
        :param builtin: True if this is a built-in layout (internal use).
        :raises ValueError: If name conflicts with a built-in layout.
        """
        entry = LayoutEntry(
            name=name,
            factory=factory,
            description=description,
            builtin=builtin,
        )

        with self._lock:
            if name in self._layouts and self._layouts[name].builtin and not builtin:
                raise ValueError(
                    f"Cannot override built-in layout '{name}'. Use a different name."
                )
            self._layouts[name] = entry

    def unregister_layout(self, name: str) -> None:
        """Unregister a custom layout.

        :param name: Layout name to unregister.
        :raises KeyError: If layout is not registered.
        :raises ValueError: If trying to unregister a built-in layout.
        """
        with self._lock:
            if name not in self._layouts:
                raise KeyError(f"Layout '{name}' is not registered")
            if self._layouts[name].builtin:
                raise ValueError(f"Cannot unregister built-in layout '{name}'")
            del self._layouts[name]

    def get_layout(self, name: str) -> LayoutEntry[TLayout] | None:
        """Get a layout entry by name.

        :param name: Layout name.
        :return: Layout entry or None if not found.
        """
        return self._layouts.get(name)

    def has_layout(self, name: str) -> bool:
        """Check if a layout is registered.

        :param name: Layout name.
        :return: True if layout is registered.
        """
        with self._lock:
            return name in self._layouts

    def clear_layouts(self) -> None:
        """Clear all custom layouts, keeping built-ins.

        Primarily for testing.
        """
        with self._lock:
            self._layouts = {k: v for k, v in self._layouts.items() if v.builtin}
