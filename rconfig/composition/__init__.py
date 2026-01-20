"""Config composition subsystem.

Handles _ref_ resolution, deep merging, _instance_ resolution,
and provenance tracking.

The composition uses an incremental algorithm that only loads files
needed for the requested inner_path (lazy composition optimization).
"""

from .composer import ConfigComposer, compose, compose_with_provenance
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

# Re-export provenance classes from their new location for backwards compatibility
from rconfig.provenance import (
    Provenance,
    ProvenanceEntry,
    ProvenanceNode,
    InstanceRef,
    EntrySourceType,
    NodeSourceType,
    ProvenanceLayout,
    ProvenanceFormatContext,
    ProvenanceFormat,
    ProvenanceTreeLayout,
    TreeLayout,  # Backwards compatibility alias
    # Registry
    ProvenancePresetEntry,
    ProvenanceRegistry,
    get_provenance_registry,
)

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
    "ProvenanceFormatContext",
    "ProvenanceFormat",
    "ProvenanceTreeLayout",
    "TreeLayout",  # Backwards compatibility alias
    # Registry
    "ProvenancePresetEntry",
    "ProvenanceRegistry",
    "get_provenance_registry",
    # Errors
    "AmbiguousRefError",
]
