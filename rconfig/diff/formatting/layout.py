"""Diff layout system for customizable formatting.

This module provides the base classes for diff layouts.
Layouts define HOW to render pre-processed diff data,
not WHAT to show (that's handled by the format class).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .model import DiffDisplayModel


class DiffLayout(ABC):
    """Base class for diff formatting layouts.

    A layout defines HOW to render diff information.
    It receives a DiffDisplayModel with data to display
    and is responsible only for converting it to the desired
    output format (text, HTML, markdown, etc.).

    Example::

        class SimpleLayout(DiffLayout):
            def render(self, model):
                if model.empty_message:
                    return model.empty_message
                lines = []
                for entry in model.entries:
                    indicator = entry.diff_type.indicator
                    lines.append(f"{indicator} {entry.path}")
                return "\\n".join(lines)
    """

    @abstractmethod
    def render(self, model: DiffDisplayModel) -> str:
        """Render the diff model to string output.

        This is the main entry point called by DiffFormat.__str__().

        :param model: The display model with data to render.
        :return: Formatted string representation.
        """
        ...
