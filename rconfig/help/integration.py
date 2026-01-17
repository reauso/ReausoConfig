"""Help integration system for CLI help generation.

This module provides the HelpIntegration abstract base class and
FunctionHelpIntegration wrapper for custom help handlers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from rconfig.provenance import Provenance


class HelpIntegration(ABC):
    """Base class for CLI help integrations.

    Subclass this to customize how config help is integrated into CLI.
    The integrate() method is called when --help or -h is detected.

    :param consume_help_flag: If True (default), remove --help/-h from sys.argv
                              before calling integrate(). Set to False if your
                              integration passes control to another parser
                              (like argparse) that handles --help itself.

    Example::

        class JsonHelpIntegration(HelpIntegration):
            def __init__(self):
                super().__init__(consume_help_flag=True)

            def integrate(self, provenance: Provenance, config_path: str) -> None:
                import json
                import sys
                data = [{"path": p, "type": str(e.type_hint)} for p, e in provenance.items()]
                print(json.dumps(data, indent=2))
                sys.exit(0)

        rc.set_help_integration(JsonHelpIntegration())
    """

    def __init__(self, *, consume_help_flag: bool = True) -> None:
        """Initialize the integration.

        :param consume_help_flag: If True, remove --help/-h from sys.argv.
        """
        self._consume_help_flag = consume_help_flag

    @property
    def consume_help_flag(self) -> bool:
        """Whether to consume --help/-h from sys.argv before integrate()."""
        return self._consume_help_flag

    @abstractmethod
    def integrate(self, provenance: Provenance, config_path: str) -> None:
        """Integrate help for config entries into CLI.

        :param provenance: Provenance data with type hints and descriptions.
        :param config_path: Path to the config file.
        """
        ...


class FunctionHelpIntegration(HelpIntegration):
    """Wraps a plain function as a HelpIntegration.

    Used internally by the @help_integration decorator.
    The decorator does NOT auto-exit - the user's function
    is responsible for all behavior including sys.exit() if desired.
    """

    def __init__(self, func: Callable[[Provenance, str], None]) -> None:
        """Initialize with the handler function.

        :param func: A function with signature (provenance, config_path) -> None.
        """
        super().__init__(consume_help_flag=True)
        self._func = func

    def integrate(self, provenance: Provenance, config_path: str) -> None:
        """Delegate to the wrapped function.

        :param provenance: Provenance data with type hints and descriptions.
        :param config_path: Path to the config file.
        """
        self._func(provenance, config_path)
