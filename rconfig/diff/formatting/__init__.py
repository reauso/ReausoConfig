"""Diff formatting subsystem.

This module provides customizable formatting for diff output,
including layouts, format builders, and presets.
"""

from .model import (
    DiffDisplayModel,
    DiffDisplayModelBuilder,
    DiffEntryDisplayModel,
)
from .flat import DiffFlatLayout
from .format import DiffFormat, DiffFormatContext, DiffPreset
from .layout import DiffLayout
from .markdown import DiffMarkdownLayout
from .tree import DiffTreeLayout

__all__ = [
    # Format builder
    "DiffFormat",
    "DiffFormatContext",
    "DiffPreset",
    # Display model
    "DiffDisplayModel",
    "DiffDisplayModelBuilder",
    "DiffEntryDisplayModel",
    # Layout system
    "DiffLayout",
    "DiffFlatLayout",
    "DiffTreeLayout",
    "DiffMarkdownLayout",
]
