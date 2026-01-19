"""Provenance layout system for customizable formatting.

This module provides the base classes for provenance layouts.
Layouts define HOW to render display model data,
not WHAT to show (that's handled by ProvenanceFormat).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .model import ProvenanceDisplayModel


class ProvenanceLayout(ABC):
    """Base class for provenance formatting layouts.

    A layout defines HOW to render provenance information.
    It receives a ProvenanceDisplayModel with data to display
    and is responsible for converting it to the desired
    output format (text, HTML, etc.).

    Example::

        class TableLayout(ProvenanceLayout):
            def render(self, model):
                if model.empty_message:
                    return model.empty_message
                lines = []
                for entry in model.entries:
                    lines.append(f"| /{entry.path} | {entry.file}:{entry.line} |")
                return "\\n".join(lines)
    """

    @abstractmethod
    def render(self, model: ProvenanceDisplayModel) -> str:
        """Render the provenance model to string output.

        This is the main entry point called by ProvenanceFormat.__str__().

        :param model: The display model containing data to render.
        :return: Formatted string representation.
        """
        ...
