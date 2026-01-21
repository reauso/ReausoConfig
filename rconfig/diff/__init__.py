"""Config diffing subsystem.

Compares two configurations and reports differences.
Supports multiple output formats and layouts.

Usage::

    import rconfig as rc
    from pathlib import Path

    # Compare two configs
    diff = rc.diff(Path("config_v1.yaml"), Path("config_v2.yaml"))

    # Access differences
    for path, entry in diff.added.items():
        print(f"Added: {path} = {entry.right_value}")

    # Format output
    print(diff.format().terminal())
    print(diff.format().markdown())
    print(diff.format().show_provenance().tree())
"""

# Core models
from .models import DiffEntry, DiffEntryType

# Main classes
from .diff import ConfigDiff
from .builder import DiffBuilder

# Formatting subsystem
from .formatting import (
    DiffFormat,
    DiffFormatContext,
    DiffLayout,
    DiffFlatLayout,
    DiffTreeLayout,
    DiffMarkdownLayout,
    # Registry
    DiffLayoutEntry,
    DiffPresetEntry,
    DiffRegistry,
    get_diff_registry,
)

__all__ = [
    # Enums
    "DiffEntryType",
    # Data classes
    "DiffEntry",
    # Main classes
    "ConfigDiff",
    "DiffBuilder",
    # Formatting
    "DiffFormat",
    "DiffFormatContext",
    "DiffLayout",
    "DiffFlatLayout",
    "DiffTreeLayout",
    "DiffMarkdownLayout",
    # Registry
    "DiffLayoutEntry",
    "DiffPresetEntry",
    "DiffRegistry",
    "get_diff_registry",
]
