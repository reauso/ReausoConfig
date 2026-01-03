"""Abstract base class for config exporters.

This module defines the interface that all config exporters must implement,
enabling support for multiple output formats (dict, YAML, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any


class Exporter(ABC):
    """Abstract base class for config exporters.

    Subclass this to add support for new export formats.
    Implementations convert a resolved config dictionary to a specific
    output format (dict, YAML string, etc.).

    Exporters are configured via constructor arguments, not method arguments.
    This ensures consistent configuration across multiple export calls.

    Example::

        class TomlExporter(Exporter):
            def __init__(self, *, multiline_strings: bool = False) -> None:
                self._multiline_strings = multiline_strings

            def export(self, config: dict[str, Any]) -> str:
                import tomli_w
                return tomli_w.dumps(config)
    """

    @abstractmethod
    def export(self, config: dict[str, Any]) -> Any:
        """Export the resolved config to the target format.

        :param config: Fully resolved config dictionary (interpolations resolved,
                       _target_, _ref_, _instance_ markers still present).
        :return: The exported data in the target format.
        """
