"""Built-in provenance formatting presets.

This module registers all built-in presets using the public registry API.
"""

from .format import ProvenanceFormatContext
from .registry import get_provenance_registry


def _register_builtins() -> None:
    """Register all built-in provenance presets."""
    registry = get_provenance_registry()

    # DEFAULT preset - matches ProvenanceFormatContext defaults
    registry.register_preset(
        name="default",
        factory=lambda: ProvenanceFormatContext(
            show_paths=True,
            show_values=True,
            show_files=True,
            show_lines=True,
            show_source_type=True,
            show_chain=True,
            show_overrides=True,
            show_targets=True,
            show_deprecations=True,
            show_types=False,
            show_descriptions=False,
        ),
        description="Default format settings.",
        builtin=True,
    )

    # MINIMAL preset
    registry.register_preset(
        name="minimal",
        factory=lambda: ProvenanceFormatContext(
            show_paths=True,
            show_values=False,
            show_files=True,
            show_lines=True,
            show_source_type=False,
            show_chain=False,
            show_overrides=False,
            show_targets=False,
        ),
        description="Show only paths, files, and lines.",
        builtin=True,
    )

    # COMPACT preset
    registry.register_preset(
        name="compact",
        factory=lambda: ProvenanceFormatContext(
            show_paths=True,
            show_values=True,
            show_files=True,
            show_lines=True,
            show_source_type=True,
            show_chain=False,
            show_overrides=False,
            show_targets=True,
            show_types=True,
            show_descriptions=False,
        ),
        description="Show paths, values, files, lines, source type, targets, types.",
        builtin=True,
    )

    # FULL preset
    registry.register_preset(
        name="full",
        factory=lambda: ProvenanceFormatContext(
            show_paths=True,
            show_values=True,
            show_files=True,
            show_lines=True,
            show_source_type=True,
            show_chain=True,
            show_overrides=True,
            show_targets=True,
            show_types=True,
            show_descriptions=True,
        ),
        description="Show everything including chains, overrides, types, descriptions.",
        builtin=True,
    )

    # VALUES preset - simple key=value view
    registry.register_preset(
        name="values",
        factory=lambda: ProvenanceFormatContext(
            show_paths=True,
            show_values=True,
            show_files=False,
            show_lines=False,
            show_source_type=False,
            show_chain=False,
            show_overrides=False,
            show_targets=False,
            show_deprecations=False,
            show_types=False,
            show_descriptions=False,
        ),
        description="Show only paths and values (simple key=value view).",
        builtin=True,
    )

    # HELP preset
    registry.register_preset(
        name="help",
        factory=lambda: ProvenanceFormatContext(
            show_paths=True,
            show_types=True,
            show_values=True,
            show_descriptions=True,
            show_files=False,
            show_lines=False,
            show_source_type=False,
            show_chain=False,
            show_overrides=False,
            show_targets=False,
            show_deprecations=False,
        ),
        description="Show paths, types, values, descriptions for CLI help.",
        builtin=True,
    )

    # DEPRECATIONS preset
    registry.register_preset(
        name="deprecations",
        factory=lambda: ProvenanceFormatContext(
            show_paths=True,
            show_values=True,
            show_files=True,
            show_lines=True,
            show_source_type=False,
            show_chain=False,
            show_overrides=False,
            show_targets=False,
            show_deprecations=True,
            deprecations_only=True,
        ),
        description="Show only deprecated keys.",
        builtin=True,
    )


# Register built-ins at module import
_register_builtins()
