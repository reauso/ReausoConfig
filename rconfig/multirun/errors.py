"""Error classes for multirun functionality.

This module defines exceptions specific to multirun operations including
sweep validation, configuration generation, and run management.
"""

from rconfig.errors import ConfigError


class MultirunError(ConfigError):
    """Base exception for multirun-related errors."""


class InvalidSweepValueError(MultirunError):
    """Raised when a sweep value is invalid for the target parameter type.

    This occurs when sweeping a list-type parameter without using list[list].

    :param path: The parameter path being swept.
    :param expected: Expected value format (e.g., "list[list[...]]").
    :param actual: Actual type of the problematic value.
    :param index: Index in the sweep list where the error occurred.
    """

    def __init__(
        self,
        path: str,
        expected: str,
        actual: str,
        index: int,
    ) -> None:
        self.path = path
        self.expected = expected
        self.actual = actual
        self.index = index

        super().__init__(
            f"Invalid sweep value for '{path}' at index {index}. "
            f"Parameter expects a list type, so sweep values must be {expected}, "
            f"got {actual}.\n"
            f"Hint: For list-type parameters, wrap each sweep value in a list:\n"
            f'  sweep={{"{path}": [["a", "b"], ["c", "d"]]}}'
        )


class NoRunConfigurationError(MultirunError):
    """Raised when neither experiments nor sweep is provided.

    :param has_overrides: Whether constant overrides were provided.
    """

    def __init__(self, has_overrides: bool) -> None:
        self.has_overrides = has_overrides

        if has_overrides:
            hint = (
                "You provided 'overrides' but no 'sweep' or 'experiments'. "
                "For a single run, use 'instantiate()' instead."
            )
        else:
            hint = "Provide at least one of 'sweep' or 'experiments'."

        super().__init__(f"No run configuration provided for multirun. {hint}")
