"""Registry for diff formatting presets and layouts.

Thread-safe: All operations on DiffRegistry are protected by an internal lock.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Callable

from rconfig._internal import Singleton

if TYPE_CHECKING:
    from .format import DiffFormatContext


@dataclass(frozen=True, kw_only=True)
class DiffPresetEntry:
    """Immutable entry for a registered diff format preset.

    :param name: Unique identifier for the preset.
    :param factory: Callable returning a DiffFormatContext with preset settings.
    :param description: Human-readable description.
    :param builtin: True if this is a built-in preset.
    """

    name: str
    factory: Callable[[], DiffFormatContext]
    description: str = ""
    builtin: bool = False


@Singleton
class DiffRegistry:
    """Thread-safe registry for diff formatting presets and layouts.

    Example::

        from rconfig.diff.formatting import (
            DiffRegistry,
            DiffFormatContext,
        )

        registry = DiffRegistry()

        # Register a custom preset
        def my_preset():
            return DiffFormatContext(
                show_added=True,
                show_removed=False,
                show_changed=True,
            )

        registry.register_preset("my_preset", my_preset, "My custom preset")

        # Use it
        print(diff.format().preset("my_preset"))
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        self._presets: dict[str, DiffPresetEntry] = {}
        self._lock = threading.RLock()

    # --- Preset Methods ---

    @property
    def known_presets(self) -> MappingProxyType[str, DiffPresetEntry]:
        """Read-only view of all registered presets."""
        return MappingProxyType(self._presets)

    def register_preset(
        self,
        name: str,
        factory: Callable[[], DiffFormatContext],
        description: str = "",
        *,
        builtin: bool = False,
    ) -> None:
        """Register a format preset.

        :param name: Preset name.
        :param factory: Callable returning DiffFormatContext.
        :param description: Human-readable description.
        :param builtin: True if this is a built-in preset (internal use).
        :raises ValueError: If name conflicts with a built-in preset.
        """
        entry = DiffPresetEntry(
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

    def get_preset(self, name: str) -> DiffPresetEntry | None:
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

    def clear(self) -> None:
        """Clear all custom presets, keeping built-ins.

        Primarily for testing.
        """
        with self._lock:
            self._presets = {k: v for k, v in self._presets.items() if v.builtin}


def get_diff_registry() -> DiffRegistry:
    """Get the global diff registry instance.

    :return: The singleton DiffRegistry instance.
    """
    return DiffRegistry()
