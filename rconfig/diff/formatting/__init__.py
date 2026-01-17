"""Diff formatting subsystem.

This module provides customizable formatting for diff output,
including layouts, format builders, and presets.
"""

from .format import DiffFormat, DiffPreset
from .layout import DiffFormatContext, DiffLayout
from .flat import DiffFlatLayout
from .tree import DiffTreeLayout
from .markdown import DiffMarkdownLayout

__all__ = [
    # Format builder
    "DiffFormat",
    "DiffPreset",
    # Layout system
    "DiffFormatContext",
    "DiffLayout",
    "DiffFlatLayout",
    "DiffTreeLayout",
    "DiffMarkdownLayout",
]
