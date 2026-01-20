"""Built-in diff formatting presets.

This module registers all built-in presets using the public registry API.
"""

from .format import DiffFormatContext
from .registry import get_diff_registry


def _register_builtins() -> None:
    """Register all built-in diff presets."""
    registry = get_diff_registry()

    # DEFAULT preset - matches DiffFormatContext defaults
    registry.register_preset(
        name="default",
        factory=lambda: DiffFormatContext(
            show_paths=True,
            show_values=True,
            show_files=True,
            show_lines=True,
            show_provenance=False,
            show_unchanged=False,
            show_added=True,
            show_removed=True,
            show_changed=True,
            show_counts=True,
        ),
        description="Default format settings.",
        builtin=True,
    )

    # CHANGES_ONLY preset
    registry.register_preset(
        name="changes_only",
        factory=lambda: DiffFormatContext(
            show_added=True,
            show_removed=True,
            show_changed=True,
            show_unchanged=False,
            show_counts=True,
        ),
        description="Only added/removed/changed entries.",
        builtin=True,
    )

    # WITH_CONTEXT preset
    registry.register_preset(
        name="with_context",
        factory=lambda: DiffFormatContext(
            show_added=True,
            show_removed=True,
            show_changed=True,
            show_unchanged=True,
            show_counts=True,
        ),
        description="Changes plus unchanged entries.",
        builtin=True,
    )

    # FULL preset
    registry.register_preset(
        name="full",
        factory=lambda: DiffFormatContext(
            show_added=True,
            show_removed=True,
            show_changed=True,
            show_unchanged=True,
            show_provenance=True,
            show_counts=True,
        ),
        description="All entries including unchanged with provenance.",
        builtin=True,
    )

    # SUMMARY preset
    registry.register_preset(
        name="summary",
        factory=lambda: DiffFormatContext(
            show_added=False,
            show_removed=False,
            show_changed=False,
            show_unchanged=False,
            show_counts=True,
        ),
        description="Only statistics, no individual entries.",
        builtin=True,
    )


# Register built-ins at module import
_register_builtins()
