"""Config composition subsystem.

Handles _ref_ resolution, deep merging, _instance_ resolution,
and provenance tracking.

The composition uses an incremental algorithm that only loads files
needed for the requested inner_path (lazy composition optimization).
"""

from .Composer import ConfigComposer, compose, compose_with_provenance
from .IncrementalComposer import (
    IncrementalComposer,
    BlockingRef,
    InstanceMarker,
    CompositionResult,
    set_cache_size,
    clear_cache,
)
from .DependencyAnalyzer import DependencyAnalyzer
from .CompositionCache import (
    CompositionCache,
    CachedFile,
    CachedComposition,
    get_global_cache,
    clear_global_cache,
    set_global_cache_size,
)
from .Merger import deep_merge
from .InstanceResolver import InstanceResolver
from .Provenance import (
    Provenance,
    ProvenanceEntry,
    ProvenanceNode,
    InstanceRef,
    EntrySourceType,
    NodeSourceType,
)
from .ProvenanceLayout import ProvenanceLayout, FormatContext
from .ProvenanceFormat import ProvenanceFormat, ProvenancePreset
from .TreeLayout import TreeLayout

from rconfig.errors import AmbiguousRefError

__all__ = [
    # Composer
    "ConfigComposer",
    "compose",
    "compose_with_provenance",
    # Incremental composition
    "IncrementalComposer",
    "BlockingRef",
    "InstanceMarker",
    "CompositionResult",
    # Dependency analysis
    "DependencyAnalyzer",
    # Caching
    "CompositionCache",
    "CachedFile",
    "CachedComposition",
    "get_global_cache",
    "clear_global_cache",
    "set_global_cache_size",
    # Cache management
    "set_cache_size",
    "clear_cache",
    # Merge
    "deep_merge",
    # Instance resolution
    "InstanceResolver",
    # Provenance
    "Provenance",
    "ProvenanceEntry",
    "ProvenanceNode",
    "InstanceRef",
    "EntrySourceType",
    "NodeSourceType",
    "ProvenanceLayout",
    "FormatContext",
    "ProvenanceFormat",
    "ProvenancePreset",
    "TreeLayout",
    # Errors
    "AmbiguousRefError",
]
