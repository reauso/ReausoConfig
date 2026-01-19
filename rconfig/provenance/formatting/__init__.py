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
from .format import ProvenanceFormat, ProvenanceFormatContext, ProvenancePreset
from .layout import ProvenanceLayout
from .markdown import ProvenanceMarkdownLayout
from .tree import ProvenanceTreeLayout

# Backwards compatibility alias
TreeLayout = ProvenanceTreeLayout

__all__ = [
    # Format builder
    "ProvenanceFormat",
    "ProvenancePreset",
    # Display models
    "InterpolationKind",
    "InterpolationNodeDisplayModel",
    "ProvenanceDisplayModel",
    "ProvenanceDisplayModelBuilder",
    "ProvenanceEntryDisplayModel",
    # Layout system
    "ProvenanceFormatContext",
    "ProvenanceLayout",
    "ProvenanceFlatLayout",
    "ProvenanceMarkdownLayout",
    "ProvenanceTreeLayout",
    "TreeLayout",  # Backwards compatibility alias
]
