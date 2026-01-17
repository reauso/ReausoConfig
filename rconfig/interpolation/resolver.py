"""Interpolation resolver for config values.

This module provides the InterpolationResolver class that walks a config tree,
finds interpolation patterns (${...}), and resolves them to their final values.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rconfig._internal.path_utils import build_child_path
from rconfig.errors import (
    CircularInterpolationError,
    EnvironmentVariableError,
    InterpolationError,
    InterpolationResolutionError,
)
from rconfig.interpolation.evaluator import EvalResult, ExpressionEvaluator, InterpolationSource
from rconfig.interpolation.parser import (
    InterpolationParser,
    find_interpolations,
    has_interpolation,
    is_standalone_interpolation,
)

if TYPE_CHECKING:
    from rconfig.provenance import ProvenanceBuilder


class InterpolationResolver:
    """Resolves all interpolations in a config tree.

    Walks the config recursively, finds ${...} patterns in string values,
    parses and evaluates them, and replaces them with resolved values.

    Features:
    - Standalone interpolations (${expr}) preserve type
    - Embedded interpolations (text ${expr} text) become strings
    - Circular reference detection
    - Provenance tracking for debugging

    :param config: The composed config dictionary to resolve.
    :param provenance: Optional ProvenanceBuilder for tracking sources.

    Example::

        config = {
            "defaults": {"lr": 0.01},
            "model": {"learning_rate": "${/defaults.lr}"},
        }
        resolver = InterpolationResolver(config)
        resolved = resolver.resolve_all()
        # resolved["model"]["learning_rate"] == 0.01
    """

    def __init__(
        self,
        config: dict[str, Any],
        provenance: "ProvenanceBuilder | None" = None,
    ) -> None:
        self._original_config = config
        self._provenance = provenance
        self._parser = InterpolationParser()
        self._resolving_paths: set[str] = set()  # Config paths being resolved
        self._cache: dict[str, Any] = {}  # Cache resolved values by path

    def resolve_all(self) -> dict[str, Any]:
        """Resolve all interpolations in the config tree.

        :return: New config dict with all interpolations resolved.
        :raises CircularInterpolationError: If circular references are detected.
        :raises InterpolationSyntaxError: If an expression cannot be parsed.
        :raises InterpolationResolutionError: If a reference cannot be resolved.
        :raises EnvironmentVariableError: If a required env var is not set.
        """
        return self._resolved_value(self._original_config, "")

    def get_resolved_value(self, path: str) -> tuple[Any, "InterpolationSource | None"]:
        """Get a resolved value at a config path.

        This method is called by the evaluator when resolving config references.
        It ensures values are resolved (if they contain interpolations) and
        detects circular references.

        :param path: The config path to resolve.
        :return: Tuple of (resolved_value, interpolation_source).
        :raises CircularInterpolationError: If circular reference detected.
        :raises InterpolationResolutionError: If path not found.
        """
        from rconfig._internal.path_utils import get_value_at_path
        from rconfig.errors import InterpolationResolutionError

        # Check cache first
        if path in self._cache:
            return self._cache[path]

        # Check for circular reference
        if path in self._resolving_paths:
            raise CircularInterpolationError(list(self._resolving_paths) + [path])

        # Get raw value from original config
        try:
            raw_value = get_value_at_path(self._original_config, path)
        except (KeyError, IndexError, TypeError) as e:
            raise InterpolationResolutionError(
                path,
                f"path not found in config: {e}",
                hint="Verify the path exists in the config. Use dot notation (e.g., 'model.lr').",
            ) from e

        # If value contains interpolations, resolve it
        self._resolving_paths.add(path)
        try:
            resolved = self._resolved_value(raw_value, path)

            # Get provenance info
            source: InterpolationSource | None = None
            if self._provenance:
                entry = self._provenance.get(path)
                if entry:
                    source = InterpolationSource(
                        kind="config",
                        expression=path,
                        value=resolved,
                        path=path,
                        file=entry.file,
                        line=entry.line,
                    )
            if source is None:
                source = InterpolationSource(
                    kind="config",
                    expression=path,
                    value=resolved,
                    path=path,
                )

            # Cache the result
            self._cache[path] = (resolved, source)
            return resolved, source
        finally:
            self._resolving_paths.discard(path)

    def _resolved_value(self, value: Any, path: str) -> Any:
        """Return value with all interpolations resolved.

        :param value: The value to resolve (may be dict, list, string, or scalar).
        :param path: Current config path for error messages and provenance.
        :return: Resolved value.
        """
        if isinstance(value, str):
            if has_interpolation(value):
                return self._resolved_string(value, path)
            return value
        elif isinstance(value, dict):
            return {
                k: self._resolved_value(v, build_child_path(path, k))
                for k, v in value.items()
            }
        elif isinstance(value, list):
            return [
                self._resolved_value(item, build_child_path(path, i))
                for i, item in enumerate(value)
            ]
        return value

    def _resolved_string(self, value: str, path: str) -> Any:
        """Return string with all interpolations resolved.

        :param value: The string containing ${...} patterns.
        :param path: Current config path for error messages.
        :return: Resolved value (preserves type for standalone, string for embedded).

        Note: Circular reference detection is handled by get_resolved_value(),
        which is called by the evaluator when resolving config path references.
        """
        if is_standalone_interpolation(value):
            # Standalone interpolation: ${expr} - preserve type
            expr = value[2:-1]  # Remove ${ and }
            result = self._evaluate_expression(expr, path)
            self._update_provenance(path, result)
            return result.value
        else:
            # Embedded interpolations: replace each ${...} with string
            matches = find_interpolations(value)
            result_parts: list[str] = []
            sources: list[InterpolationSource] = []
            last_end = 0

            for match in matches:
                # Add text before this interpolation
                if match.start > last_end:
                    result_parts.append(value[last_end : match.start])

                # Evaluate and convert to string
                eval_result = self._evaluate_expression(match.expression, path)
                result_parts.append(str(eval_result.value))
                sources.append(eval_result.source)
                last_end = match.end

            # Add remaining text after last interpolation
            if last_end < len(value):
                result_parts.append(value[last_end:])

            final_value = "".join(result_parts)

            # Update provenance with compound source
            if self._provenance and sources:
                compound_source = InterpolationSource(
                    kind="expression",
                    expression=value,
                    value=final_value,
                    sources=sources,
                    operator="concat",
                )
                self._update_provenance_with_source(path, compound_source)

            return final_value

    def _evaluate_expression(self, expr: str, path: str) -> EvalResult:
        """Parse and evaluate an interpolation expression.

        :param expr: The expression to evaluate (without ${}).
        :param path: Current config path for error messages.
        :return: Evaluation result with value and provenance info.
        """
        from lark.exceptions import VisitError

        from rconfig.interpolation.registry import ResolverRegistry

        # Parse the expression
        tree = self._parser.parse(expr)

        # Create evaluator that calls back to resolver for config lookups
        evaluator = ExpressionEvaluator(
            config=self._original_config,
            provenance=self._provenance,
            resolver=self,  # Pass resolver for circular detection
            registry=ResolverRegistry(),  # Pass registry for app resolvers
        )

        # Transform the tree to get the result
        try:
            result = evaluator.transform(tree)
        except VisitError as e:
            # Unwrap our custom errors from Lark's VisitError
            if isinstance(e.orig_exc, InterpolationError):
                raise e.orig_exc from None
            # Wrap common Python errors as InterpolationResolutionError
            if isinstance(e.orig_exc, ZeroDivisionError):
                raise InterpolationResolutionError(
                    expr,
                    f"division by zero: {e.orig_exc}",
                    hint="Check that divisors are not zero.",
                ) from e.orig_exc
            if isinstance(e.orig_exc, IndexError):
                raise InterpolationResolutionError(
                    expr,
                    f"index out of bounds: {e.orig_exc}",
                    hint="Check that list indices are within bounds.",
                ) from e.orig_exc
            if isinstance(e.orig_exc, TypeError):
                raise InterpolationResolutionError(
                    expr,
                    f"type error: {e.orig_exc}",
                    hint="Check that the operation is valid for the value types.",
                ) from e.orig_exc
            raise

        return result

    def _update_provenance(self, path: str, result: EvalResult) -> None:
        """Update provenance entry for a resolved path.

        :param path: The config path.
        :param result: The evaluation result with source info.
        """
        self._update_provenance_with_source(path, result.source)

    def _update_provenance_with_source(
        self, path: str, source: InterpolationSource
    ) -> None:
        """Update provenance entry with an interpolation source.

        :param path: The config path.
        :param source: The interpolation source to record.
        """
        if self._provenance is None:
            return

        entry = self._provenance.get_entry(path)
        if entry:
            # Update existing entry with interpolation info and resolved value
            entry.interpolation = source
            entry.value = source.value


def resolve_interpolations(
    config: dict[str, Any],
    provenance: "ProvenanceBuilder | None" = None,
) -> dict[str, Any]:
    """Convenience function to resolve all interpolations in a config.

    :param config: The composed config dictionary.
    :param provenance: Optional ProvenanceBuilder for tracking.
    :return: Config with all interpolations resolved.

    Example::

        config = compose("app.yaml")
        resolved = resolve_interpolations(config)
    """
    resolver = InterpolationResolver(config, provenance)
    return resolver.resolve_all()
