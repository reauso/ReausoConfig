"""Built-in provenance formatting layouts.

This module registers all built-in layouts using the public registry API.
"""

from .flat import ProvenanceFlatLayout
from .markdown import ProvenanceMarkdownLayout
from .registry import get_provenance_registry
from .tree import ProvenanceTreeLayout


def _register_builtins() -> None:
    """Register all built-in provenance layouts."""
    registry = get_provenance_registry()

    # TREE layout (default)
    registry.register_layout(
        name="tree",
        factory=lambda: ProvenanceTreeLayout(),
        description="Tree-style multiline format with connectors.",
        builtin=True,
    )

    # FLAT layout
    registry.register_layout(
        name="flat",
        factory=lambda: ProvenanceFlatLayout(),
        description="Single-line compact format.",
        builtin=True,
    )

    # MARKDOWN layout
    registry.register_layout(
        name="markdown",
        factory=lambda: ProvenanceMarkdownLayout(),
        description="Markdown table format for documentation.",
        builtin=True,
    )


# Register built-ins at module import
_register_builtins()
