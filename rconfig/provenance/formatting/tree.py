"""Tree-style layout for provenance formatting.

This module provides a tree layout that displays provenance
in a multiline format with tree connectors (+-- and |--).
"""

from __future__ import annotations

from fnmatch import fnmatch
from typing import TYPE_CHECKING, Any

from .layout import ProvenanceFormatContext, ProvenanceLayout

if TYPE_CHECKING:
    from rconfig.provenance.provenance import Provenance
    from rconfig.provenance.models import ProvenanceEntry, ProvenanceNode


class TreeLayout(ProvenanceLayout):
    """Tree-style text layout for provenance.

    Displays provenance in a multiline format with tree structures
    for interpolation chains, using +-- and |-- connectors.

    Example output::

        /model.lr = 0.01
          config.yaml:5
          Interpolation: ${/defaults.lr * 2}
            +-- * (multiply)
                 |-- /defaults.lr = 0.005
                 |     defaults.yaml:3
                 +-- 2 (literal)
          Overrode: base.yaml:10
    """

    def get_default_context(self) -> ProvenanceFormatContext:
        """Return default settings for TreeLayout (show everything).

        :return: ProvenanceFormatContext with all options enabled.
        """
        return ProvenanceFormatContext(
            show_paths=True,
            show_values=True,
            show_files=True,
            show_lines=True,
            show_source_type=True,
            show_chain=True,
            show_overrides=True,
            show_targets=True,
            show_deprecations=True,
            show_types=False,
            show_descriptions=False,
            deprecations_only=False,
            indent_size=2,
        )

    def format_provenance(self, provenance: Provenance, ctx: ProvenanceFormatContext) -> str:
        """Format the entire provenance object.

        :param provenance: The provenance to format.
        :param ctx: Format context with show/hide settings.
        :return: Formatted string.
        """
        entries: list[str] = []

        for path, entry in provenance.items():
            # Apply filters
            if not self._matches_filters(path, entry, ctx):
                continue

            # Filter for deprecations_only mode
            if ctx.deprecations_only and entry.deprecation is None:
                continue

            formatted = self.format_entry(entry, path, ctx)
            if formatted:
                entries.append(formatted)

        result = self.join_entries(entries, ctx)

        # Add header for deprecations_only mode
        if ctx.deprecations_only:
            if entries:
                header = "Deprecated Keys:\n" + "-" * 16
                result = header + "\n\n" + result
            else:
                result = "No deprecated keys found."

        return result

    def format_entry(
        self, entry: ProvenanceEntry, path: str, ctx: ProvenanceFormatContext
    ) -> str:
        """Format a single provenance entry.

        :param entry: The entry to format.
        :param path: The config path.
        :param ctx: Format context.
        :return: Formatted entry string.
        """
        lines: list[str] = []

        # First line: path = value
        first_line_parts: list[str] = []
        if ctx.show_paths:
            first_line_parts.append(f"/{path}")
        if ctx.show_values and entry.value is not None:
            value_str = self.format_value(entry.value, ctx)
            if first_line_parts:
                first_line_parts.append(f" = {value_str}")
            else:
                first_line_parts.append(value_str)

        if first_line_parts:
            lines.append("".join(first_line_parts))

        # Location line
        location_parts: list[str] = []
        if ctx.show_source_type and entry.source_type != "file":
            source_marker = self.format_source_type(entry.source_type, ctx)
            if entry.source_type == "cli" and entry.cli_arg:
                location_parts.append(f"{source_marker}: {entry.cli_arg}")
            elif entry.source_type == "env" and entry.env_var:
                location_parts.append(f"{source_marker}: {entry.env_var}")
            else:
                location_parts.append(source_marker)
        elif ctx.show_files or ctx.show_lines:
            location = self.format_location(entry.file, entry.line, ctx)
            if location:
                location_parts.append(location)

        if location_parts:
            lines.append(self.indent(" ".join(location_parts), 1, ctx))

        # Target info
        if ctx.show_targets and entry.target_name is not None:
            target_line = self._format_target(entry, ctx)
            lines.append(self.indent(target_line, 1, ctx))

        # Interpolation chain
        if ctx.show_chain and entry.interpolation:
            lines.append(
                self.indent(
                    f"Interpolation: ${{{entry.interpolation.expression}}}", 1, ctx
                )
            )
            # Format the interpolation tree
            tree_lines = self._format_interpolation_tree(entry.interpolation, 2, ctx)
            lines.extend(tree_lines)

        # Instance chain
        if ctx.show_chain and entry.instance:
            for ref in entry.instance:
                instance_line = f"Instance: {ref.path}"
                if ctx.show_files or ctx.show_lines:
                    loc = self.format_location(ref.file, ref.line, ctx)
                    if loc:
                        instance_line += f" <- {loc}"
                lines.append(self.indent(instance_line, 1, ctx))

        # Override info
        if ctx.show_overrides and entry.overrode:
            lines.append(self.indent(self.format_override(entry.overrode, ctx), 1, ctx))

        # Deprecation info
        if ctx.show_deprecations and entry.deprecation:
            deprecation_lines = self._format_deprecation(entry.deprecation, ctx)
            for line in deprecation_lines:
                lines.append(self.indent(line, 1, ctx))

        # Type hint
        if ctx.show_types and entry.type_hint is not None:
            type_str = self.format_type_hint(entry.type_hint, ctx)
            if type_str:
                lines.append(self.indent(f"Type: {type_str}", 1, ctx))

        # Description
        if ctx.show_descriptions and entry.description is not None:
            desc_str = self.format_description(entry.description, ctx)
            if desc_str:
                lines.append(self.indent(f"Description: {desc_str}", 1, ctx))

        return "\n".join(lines)

    def _format_target(
        self,
        entry: ProvenanceEntry,
        ctx: ProvenanceFormatContext,
    ) -> str:
        """Format target class information.

        :param entry: The entry with target info.
        :param ctx: Format context.
        :return: Formatted target string.
        """
        if entry.target_class is not None and entry.target_module is not None:
            # Fully resolved: Target: resnet -> myapp.models.ResNet
            result = f"Target: {entry.target_name} -> {entry.target_module}.{entry.target_class}"
            if entry.target_auto_registered:
                result += " (auto-registered)"
            return result
        elif entry.target_class is not None:
            # Class without module (shouldn't happen normally)
            result = f"Target: {entry.target_name} -> {entry.target_class}"
            if entry.target_auto_registered:
                result += " (auto-registered)"
            return result
        else:
            # Not registered
            return f"Target: {entry.target_name} (not registered)"

    def _format_deprecation(
        self,
        deprecation: Any,  # DeprecationInfo
        ctx: ProvenanceFormatContext,
    ) -> list[str]:
        """Format deprecation information.

        :param deprecation: The deprecation info to format.
        :param ctx: Format context.
        :return: List of formatted lines.
        """
        lines: list[str] = []

        # Main deprecation line: DEPRECATED -> new_key (remove in X.X.X)
        main_parts = ["DEPRECATED"]
        if deprecation.new_key:
            main_parts.append(f"-> {deprecation.new_key}")
        if deprecation.remove_in:
            main_parts.append(f"(remove in {deprecation.remove_in})")

        lines.append(" ".join(main_parts))

        # Message on separate line if present
        if deprecation.message:
            lines.append(f"Message: {deprecation.message}")

        return lines

    def _format_interpolation_tree(
        self,
        source: Any,  # InterpolationSource
        depth: int,
        ctx: ProvenanceFormatContext,
    ) -> list[str]:
        """Format an interpolation source tree recursively.

        :param source: The interpolation source.
        :param depth: Current depth for indentation.
        :param ctx: Format context.
        :return: List of formatted lines.
        """
        lines: list[str] = []
        indent_str = " " * (depth * ctx.indent_size)

        if source.kind == "expression" and source.operator:
            # Compound expression with operator
            op_line = f"+-- {source.operator}"
            if source.value is not None and ctx.show_values:
                op_line += f" = {self.format_value(source.value, ctx)}"
            lines.append(indent_str + op_line)

            # Format children
            for i, child in enumerate(source.sources):
                is_last = i == len(source.sources) - 1
                child_lines = self._format_child_source(child, depth + 1, is_last, ctx)
                lines.extend(child_lines)

        elif source.kind == "config":
            # Config path reference
            ref_line = f"+-- {source.path}"
            if source.value is not None and ctx.show_values:
                ref_line += f" = {self.format_value(source.value, ctx)}"
            lines.append(indent_str + ref_line)

            # Show where the referenced value is defined
            if (ctx.show_files or ctx.show_lines) and source.file:
                loc = self.format_location(source.file, source.line or 0, ctx)
                lines.append(indent_str + f"     {loc}")

        elif source.kind == "env":
            # Environment variable
            env_line = f"+-- env:{source.env_var}"
            if source.value is not None and ctx.show_values:
                env_line += f" = {self.format_value(source.value, ctx)}"
            lines.append(indent_str + env_line)

        elif source.kind == "literal":
            # Literal value
            lit_line = f"+-- {self.format_value(source.value, ctx)} (literal)"
            lines.append(indent_str + lit_line)

        return lines

    def _format_child_source(
        self,
        source: Any,  # InterpolationSource
        depth: int,
        is_last: bool,
        ctx: ProvenanceFormatContext,
    ) -> list[str]:
        """Format a child source with proper tree connectors.

        :param source: The child source to format.
        :param depth: Current depth.
        :param is_last: Whether this is the last child.
        :param ctx: Format context.
        :return: List of formatted lines.
        """
        lines: list[str] = []
        indent_str = " " * (depth * ctx.indent_size)
        connector = "+--" if is_last else "|--"

        if source.kind == "expression" and source.operator:
            # Nested operator
            op_line = f"{connector} {source.operator}"
            if source.value is not None and ctx.show_values:
                op_line += f" = {self.format_value(source.value, ctx)}"
            lines.append(indent_str + op_line)

            for i, child in enumerate(source.sources):
                child_is_last = i == len(source.sources) - 1
                child_lines = self._format_child_source(
                    child, depth + 1, child_is_last, ctx
                )
                lines.extend(child_lines)

        elif source.kind == "config":
            ref_line = f"{connector} {source.path}"
            if source.value is not None and ctx.show_values:
                ref_line += f" = {self.format_value(source.value, ctx)}"
            lines.append(indent_str + ref_line)

            if (ctx.show_files or ctx.show_lines) and source.file:
                continuation = "|" if not is_last else " "
                loc = self.format_location(source.file, source.line or 0, ctx)
                lines.append(indent_str + f"{continuation}     {loc}")

        elif source.kind == "env":
            env_line = f"{connector} env:{source.env_var}"
            if source.value is not None and ctx.show_values:
                env_line += f" = {self.format_value(source.value, ctx)}"
            lines.append(indent_str + env_line)

        elif source.kind == "literal":
            lit_line = f"{connector} {self.format_value(source.value, ctx)} (literal)"
            lines.append(indent_str + lit_line)

        return lines

    def _matches_filters(
        self, path: str, entry: ProvenanceEntry, ctx: ProvenanceFormatContext
    ) -> bool:
        """Check if an entry matches the configured filters.

        :param path: The config path.
        :param entry: The provenance entry.
        :param ctx: Format context with filters.
        :return: True if entry matches all filters.
        """
        # If no filters, everything matches
        if not ctx.path_filters and not ctx.file_filters:
            return True

        # Check path filters (OR logic)
        if ctx.path_filters:
            path_match = any(
                fnmatch(f"/{path}", pattern) or fnmatch(path, pattern)
                for pattern in ctx.path_filters
            )
            if not path_match:
                return False

        # Check file filters (OR logic)
        if ctx.file_filters:
            file_match = any(
                fnmatch(entry.file, pattern) for pattern in ctx.file_filters
            )
            if not file_match:
                return False

        return True

    def format_value(self, value: Any, ctx: ProvenanceFormatContext) -> str:
        """Format a value for display.

        :param value: The value to format.
        :param ctx: Format context.
        :return: Formatted value string.
        """
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            # Show strings with quotes
            return repr(value)
        elif isinstance(value, (list, dict)):
            # Truncate complex values
            s = str(value)
            if len(s) > 50:
                return s[:47] + "..."
            return s
        else:
            return str(value)

    def join_entries(self, entries: list[str], ctx: ProvenanceFormatContext) -> str:
        """Join formatted entries with blank lines between them.

        :param entries: List of formatted entry strings.
        :param ctx: Format context.
        :return: Combined string.
        """
        return "\n\n".join(entries)
