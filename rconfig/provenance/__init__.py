"""Provenance tracking for config composition.

This module provides classes for tracking the origin of each value
in a composed configuration, including file paths, line numbers,
override information, and interpolation sources.

Example::

    from rconfig.provenance import Provenance, ProvenanceBuilder

    builder = ProvenanceBuilder()
    builder.add("model.lr", "config.yaml", 5)
    builder.set_config({"model": {"lr": 0.01}})
    provenance = builder.build()

    print(provenance.format().minimal())
"""

# Core models
from .models import (
    EntrySourceType,
    NodeSourceType,
    ProvenanceNode,
    InstanceRef,
    ProvenanceEntry,
)

# Main classes
from .provenance import Provenance
from .builder import ProvenanceBuilder

# Formatting subsystem
from .formatting import (
    ProvenanceFormat,
    ProvenancePreset,
    ProvenanceFormatContext,
    ProvenanceLayout,
    ProvenanceTreeLayout,
    TreeLayout,  # Backwards compatibility alias
)

__all__ = [
    # Enums
    "EntrySourceType",
    "NodeSourceType",
    # Data classes
    "ProvenanceNode",
    "InstanceRef",
    "ProvenanceEntry",
    # Main classes
    "Provenance",
    "ProvenanceBuilder",
    # Formatting
    "ProvenanceFormat",
    "ProvenancePreset",
    "ProvenanceFormatContext",
    "ProvenanceLayout",
    "ProvenanceTreeLayout",
    "TreeLayout",  # Backwards compatibility alias
]
