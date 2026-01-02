"""Config composition subsystem.

Handles _ref_ resolution, deep merging, _instance_ resolution,
and provenance tracking.
"""

from .Composer import ConfigComposer, compose, compose_with_provenance
from .Walker import (
    CompositionWalker,
    InstanceMarker,
    CompositionResult,
    set_cache_size,
    clear_cache,
)
from .Merger import deep_merge
from .InstanceResolver import InstanceResolver
from .Provenance import Provenance, ProvenanceEntry, ProvenanceNode, InstanceRef
from .ProvenanceLayout import ProvenanceLayout, FormatContext
from .ProvenanceFormat import ProvenanceFormat, ProvenancePreset
from .TreeLayout import TreeLayout

__all__ = [
    "ConfigComposer",
    "compose",
    "compose_with_provenance",
    "CompositionWalker",
    "InstanceMarker",
    "CompositionResult",
    "set_cache_size",
    "clear_cache",
    "deep_merge",
    "InstanceResolver",
    "Provenance",
    "ProvenanceEntry",
    "ProvenanceNode",
    "InstanceRef",
    "ProvenanceLayout",
    "FormatContext",
    "ProvenanceFormat",
    "ProvenancePreset",
    "TreeLayout",
]
