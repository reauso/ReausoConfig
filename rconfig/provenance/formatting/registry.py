"""Registry for provenance formatting presets and layouts.

Thread-safe: All operations on ProvenanceRegistry are protected by an internal lock.
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
    from .format import ProvenanceFormatContext
    from .layout import ProvenanceLayout

# Backward-compatible aliases for the generic entry classes.
ProvenancePresetEntry = PresetEntry
ProvenanceLayoutEntry = LayoutEntry


@Singleton
class ProvenanceRegistry(FormattingRegistry["ProvenanceFormatContext", "ProvenanceLayout"]):
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


def get_provenance_registry() -> ProvenanceRegistry:
    """Get the global provenance registry instance.

    :return: The singleton ProvenanceRegistry instance.
    """
    return ProvenanceRegistry()
