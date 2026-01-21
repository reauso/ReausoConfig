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
    ProvenanceLayoutEntry,
    ProvenancePresetEntry,
    ProvenanceRegistry,
    get_provenance_registry,
)

# Import builtin modules to trigger registration
from . import builtin_presets as _builtin_presets  # noqa: F401
from . import builtin_layouts as _builtin_layouts  # noqa: F401

# Backwards compatibility alias
TreeLayout = ProvenanceTreeLayout

__all__ = [
    # Format builder
    "ProvenanceFormat",
    "ProvenanceFormatContext",
    # Registry
    "ProvenanceLayoutEntry",
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
