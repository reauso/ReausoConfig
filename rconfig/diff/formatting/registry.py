"""Registry for diff formatting presets and layouts.

Thread-safe: All operations on DiffRegistry are protected by an internal lock.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rconfig._internal import Singleton
from rconfig._internal.formatting_registry import (
    FormattingRegistry,
    LayoutEntry,
    PresetEntry,
)

if TYPE_CHECKING:
    from .format import DiffFormatContext
    from .layout import DiffLayout

# Backward-compatible aliases for the generic entry classes.
DiffPresetEntry = PresetEntry
DiffLayoutEntry = LayoutEntry


@Singleton
class DiffRegistry(FormattingRegistry["DiffFormatContext", "DiffLayout"]):
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


def get_diff_registry() -> DiffRegistry:
    """Get the global diff registry instance.

    :return: The singleton DiffRegistry instance.
    """
    return DiffRegistry()
