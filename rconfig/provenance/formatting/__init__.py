"""Provenance formatting subsystem.

This module provides customizable formatting for provenance output,
including layouts, format builders, and presets.
"""

from .model import (
    InterpolationKind,
    InterpolationNodeDisplayModel,
    ProvenanceDisplayModel,
    ProvenanceDisplayModelBuilder,
    ProvenanceEntryDisplayModel,
)
from .flat import ProvenanceFlatLayout
from .format import ProvenanceFormat, ProvenanceFormatContext
from .layout import ProvenanceLayout
from .markdown import ProvenanceMarkdownLayout
from .tree import ProvenanceTreeLayout
from .registry import (
    ProvenancePresetEntry,
    ProvenanceRegistry,
    get_provenance_registry,
)

# Import presets module to trigger builtin registration
from . import presets as _presets  # noqa: F401

# Backwards compatibility alias
TreeLayout = ProvenanceTreeLayout

__all__ = [
    # Format builder
    "ProvenanceFormat",
    "ProvenanceFormatContext",
    # Registry
    "ProvenancePresetEntry",
    "ProvenanceRegistry",
    "get_provenance_registry",
    # Display models
    "InterpolationKind",
    "InterpolationNodeDisplayModel",
    "ProvenanceDisplayModel",
    "ProvenanceDisplayModelBuilder",
    "ProvenanceEntryDisplayModel",
    # Layout system
    "ProvenanceLayout",
    "ProvenanceFlatLayout",
    "ProvenanceMarkdownLayout",
    "ProvenanceTreeLayout",
    "TreeLayout",  # Backwards compatibility alias
]
