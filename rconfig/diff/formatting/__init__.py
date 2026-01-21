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
    DiffLayoutEntry,
    DiffPresetEntry,
    DiffRegistry,
    get_diff_registry,
)

# Import builtin modules to trigger registration
from . import builtin_presets as _builtin_presets  # noqa: F401
from . import builtin_layouts as _builtin_layouts  # noqa: F401

__all__ = [
    # Format builder
    "DiffFormat",
    "DiffFormatContext",
    # Registry
    "DiffLayoutEntry",
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
