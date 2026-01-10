"""Deprecation warning handlers.

This module provides the DeprecationHandler base class and default implementation
for handling deprecation warnings. Users can customize warning behavior by
subclassing DeprecationHandler or using the decorator function.
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from rconfig.deprecation.info import DeprecationInfo


class RconfigDeprecationWarning(UserWarning):
    """Warning category for rconfig deprecations.

    This warning class integrates with Python's warnings filter system,
    allowing users to control deprecation warning behavior using standard
    warnings.filterwarnings() calls.

    Example::

        import warnings

        # Ignore all rconfig deprecation warnings
        warnings.filterwarnings("ignore", category=RconfigDeprecationWarning)

        # Turn deprecation warnings into errors
        warnings.filterwarnings("error", category=RconfigDeprecationWarning)
    """

    pass


class DeprecationHandler(ABC):
    """Base class for deprecation warning handlers.

    Subclass this to customize how deprecation warnings are emitted.
    The handle() method is called for each deprecated key encountered
    when the policy is "warn".

    Example::

        class LoggingHandler(DeprecationHandler):
            def handle(
                self,
                info: DeprecationInfo,
                path: str,
                file: str,
                line: int,
            ) -> None:
                import logging
                logging.warning(f"Deprecated key '{path}' at {file}:{line}")

        rc.set_deprecation_handler(LoggingHandler())
    """

    @abstractmethod
    def handle(
        self,
        info: DeprecationInfo,
        path: str,
        file: str,
        line: int,
    ) -> None:
        """Handle a deprecation warning.

        :param info: Information about the deprecation.
        :param path: The config path that triggered the warning.
        :param file: The source file where the deprecated key was found.
        :param line: The line number in the source file.
        """
        ...


class DefaultDeprecationHandler(DeprecationHandler):
    """Default handler using Python's warnings module.

    This handler formats deprecation information into a human-readable
    message and emits it using warnings.warn() with RconfigDeprecationWarning.

    The warning message includes:
    - The deprecated path
    - The new key to use (if provided)
    - Custom message (if provided)
    - Version when the key will be removed (if provided)
    - Source file and line number
    """

    def handle(
        self,
        info: DeprecationInfo,
        path: str,
        file: str,
        line: int,
    ) -> None:
        """Emit a deprecation warning using Python's warnings module.

        :param info: Information about the deprecation.
        :param path: The config path that triggered the warning.
        :param file: The source file where the deprecated key was found.
        :param line: The line number in the source file.
        """
        msg = self._format_message(info, path, file, line)
        # stacklevel is set to skip internal frames and point to user code
        # This may need adjustment based on actual call stack depth
        warnings.warn(msg, RconfigDeprecationWarning, stacklevel=6)

    def _format_message(
        self,
        info: DeprecationInfo,
        path: str,
        file: str,
        line: int,
    ) -> str:
        """Format the deprecation warning message.

        :param info: Information about the deprecation.
        :param path: The config path that triggered the warning.
        :param file: The source file where the deprecated key was found.
        :param line: The line number in the source file.
        :return: Formatted warning message.
        """
        parts = [f"'{path}' is deprecated"]

        if info.new_key:
            parts.append(f"Use '{info.new_key}' instead")

        if info.message:
            parts.append(info.message)

        if info.remove_in:
            parts.append(f"Will be removed in version {info.remove_in}")

        parts.append(f"(at {file}:{line})")

        return ". ".join(parts)


class FunctionDeprecationHandler(DeprecationHandler):
    """Handler that wraps a plain function.

    This is used internally by the @deprecation_handler decorator to wrap
    a user-provided function as a DeprecationHandler instance.
    """

    def __init__(
        self,
        func: Callable[[DeprecationInfo, str, str, int], None],
    ) -> None:
        """Initialize with the handler function.

        :param func: A function with signature (info, path, file, line) -> None.
        """
        self._func = func

    def handle(
        self,
        info: DeprecationInfo,
        path: str,
        file: str,
        line: int,
    ) -> None:
        """Delegate to the wrapped function.

        :param info: Information about the deprecation.
        :param path: The config path that triggered the warning.
        :param file: The source file where the deprecated key was found.
        :param line: The line number in the source file.
        """
        self._func(info, path, file, line)
