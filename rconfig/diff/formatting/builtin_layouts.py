"""Built-in diff formatting layouts.

This module registers all built-in layouts using the public registry API.
"""

from .flat import DiffFlatLayout
from .markdown import DiffMarkdownLayout
from .registry import get_diff_registry
from .tree import DiffTreeLayout


def _register_builtins() -> None:
    """Register all built-in diff layouts."""
    registry = get_diff_registry()

    # FLAT layout (default for diff)
    registry.register_layout(
        name="flat",
        factory=lambda: DiffFlatLayout(),
        description="Flat single-line format.",
        builtin=True,
    )

    # TREE layout
    registry.register_layout(
        name="tree",
        factory=lambda: DiffTreeLayout(),
        description="Grouped tree-style format.",
        builtin=True,
    )

    # MARKDOWN layout
    registry.register_layout(
        name="markdown",
        factory=lambda: DiffMarkdownLayout(),
        description="Markdown table format.",
        builtin=True,
    )


# Register built-ins at module import
_register_builtins()
