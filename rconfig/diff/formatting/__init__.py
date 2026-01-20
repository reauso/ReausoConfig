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
from .format import DiffFormat, DiffFormatContext
from .layout import DiffLayout
from .markdown import DiffMarkdownLayout
from .tree import DiffTreeLayout
from .registry import (
    DiffPresetEntry,
    DiffRegistry,
    get_diff_registry,
)

# Import presets module to trigger builtin registration
from . import presets as _presets  # noqa: F401

__all__ = [
    # Format builder
    "DiffFormat",
    "DiffFormatContext",
    # Registry
    "DiffPresetEntry",
    "DiffRegistry",
    "get_diff_registry",
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
