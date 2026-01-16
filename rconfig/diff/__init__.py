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

from .Diff import ConfigDiff, DiffEntry, DiffEntryType
from .DiffBuilder import DiffBuilder
from .DiffFlatLayout import DiffFlatLayout
from .DiffFormat import DiffFormat, DiffPreset
from .DiffLayout import DiffFormatContext, DiffLayout
from .DiffMarkdownLayout import DiffMarkdownLayout
from .DiffTreeLayout import DiffTreeLayout

__all__ = [
    # Core data structures
    "ConfigDiff",
    "DiffEntry",
    "DiffEntryType",
    # Builder
    "DiffBuilder",
    # Format
    "DiffFormat",
    "DiffPreset",
    # Layout
    "DiffFormatContext",
    "DiffLayout",
    "DiffFlatLayout",
    "DiffTreeLayout",
    "DiffMarkdownLayout",
]
