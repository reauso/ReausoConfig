"""Registry for provenance formatting presets and layouts.

Thread-safe: All operations on ProvenanceRegistry are protected by an internal lock.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Callable

from rconfig._internal import Singleton

if TYPE_CHECKING:
    from .format import ProvenanceFormatContext
    from .layout import ProvenanceLayout


@dataclass(frozen=True, kw_only=True)
class ProvenancePresetEntry:
    """Immutable entry for a registered provenance format preset.

    :param name: Unique identifier for the preset (e.g., "minimal", "compact").
    :param factory: Callable returning a ProvenanceFormatContext with preset settings.
    :param description: Human-readable description.
    :param builtin: True if this is a built-in preset.
    """

    name: str
    factory: Callable[[], ProvenanceFormatContext]
    description: str = ""
    builtin: bool = False


@dataclass(frozen=True, kw_only=True)
class ProvenanceLayoutEntry:
    """Immutable entry for a registered provenance layout.

    :param name: Unique identifier for the layout (e.g., "tree", "flat", "markdown").
    :param factory: Callable returning a ProvenanceLayout instance.
    :param description: Human-readable description.
    :param builtin: True if this is a built-in layout.
    """

    name: str
    factory: Callable[[], ProvenanceLayout]
    description: str = ""
    builtin: bool = False


@Singleton
class ProvenanceRegistry:
    """Thread-safe registry for provenance formatting presets and layouts.

    Example::

        from rconfig.provenance.formatting import (
            ProvenanceRegistry,
            ProvenanceFormatContext,
        )

        registry = ProvenanceRegistry()

        # Register a custom preset
        def my_preset():
            return ProvenanceFormatContext(
                show_paths=True,
                show_values=True,
                show_files=False,
            )

        registry.register_preset("my_preset", my_preset, "My custom preset")

        # Use it
        print(prov.format().preset("my_preset"))
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        self._presets: dict[str, ProvenancePresetEntry] = {}
        self._layouts: dict[str, ProvenanceLayoutEntry] = {}
        self._lock = threading.RLock()

    # --- Preset Methods ---

    @property
    def known_presets(self) -> MappingProxyType[str, ProvenancePresetEntry]:
        """Read-only view of all registered presets."""
        return MappingProxyType(self._presets)

    def register_preset(
        self,
        name: str,
        factory: Callable[[], ProvenanceFormatContext],
        description: str = "",
        *,
        builtin: bool = False,
    ) -> None:
        """Register a format preset.

        :param name: Preset name.
        :param factory: Callable returning ProvenanceFormatContext.
        :param description: Human-readable description.
        :param builtin: True if this is a built-in preset (internal use).
        :raises ValueError: If name conflicts with a built-in preset.
        """
        entry = ProvenancePresetEntry(
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

    def get_preset(self, name: str) -> ProvenancePresetEntry | None:
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
    def known_layouts(self) -> MappingProxyType[str, ProvenanceLayoutEntry]:
        """Read-only view of all registered layouts."""
        return MappingProxyType(self._layouts)

    def register_layout(
        self,
        name: str,
        factory: Callable[[], ProvenanceLayout],
        description: str = "",
        *,
        builtin: bool = False,
    ) -> None:
        """Register a format layout.

        :param name: Layout name.
        :param factory: Callable returning ProvenanceLayout.
        :param description: Human-readable description.
        :param builtin: True if this is a built-in layout (internal use).
        :raises ValueError: If name conflicts with a built-in layout.
        """
        entry = ProvenanceLayoutEntry(
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

    def get_layout(self, name: str) -> ProvenanceLayoutEntry | None:
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


def get_provenance_registry() -> ProvenanceRegistry:
    """Get the global provenance registry instance.

    :return: The singleton ProvenanceRegistry instance.
    """
    return ProvenanceRegistry()
