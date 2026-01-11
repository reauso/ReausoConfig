"""Public API for help integrations.

This module provides the base class and built-in implementations for
CLI help integration with the rconfig configuration system.
"""

from .argparse_integration import ArgparseHelpIntegration
from .flat_integration import FlatHelpIntegration
from .grouped_integration import GroupedHelpIntegration
from .integration import FunctionHelpIntegration, HelpIntegration
from .multirun_help import MULTIRUN_HELP

__all__ = [
    "HelpIntegration",
    "FunctionHelpIntegration",
    "FlatHelpIntegration",
    "GroupedHelpIntegration",
    "ArgparseHelpIntegration",
    "MULTIRUN_HELP",
]
