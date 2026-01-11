"""CLI parsing for multirun arguments.

This module provides functionality to parse multirun-specific CLI arguments:
- Sweep syntax: `key=val1,val2` or `key=[val1, val2]`
- Experiment flags: `-e` / `--experiment`
"""

import re
from typing import Any

from rconfig.override import Override, parse_cli_arg, parse_override_key


def parse_cli_sweep_value(value: str) -> list[Any] | None:
    """Parse a CLI value that might be a sweep specification.

    Detects sweep syntax:
    - Comma-separated: `val1,val2,val3` (no quotes, no brackets)
    - Bracket syntax: `[val1, val2, val3]`

    Returns None if the value is not a sweep (single value or quoted).

    :param value: The value part of a CLI argument.
    :return: List of sweep values, or None if not a sweep.

    Examples::

        parse_cli_sweep_value("resnet,vit")          # ["resnet", "vit"]
        parse_cli_sweep_value("[resnet, vit]")       # ["resnet", "vit"]
        parse_cli_sweep_value("resnet")              # None (single value)
        parse_cli_sweep_value('"resnet,vit"')        # None (quoted = literal)
        parse_cli_sweep_value("[a,b,c]")             # ["a,b,c"] (single with commas)
    """
    # Check for quoted value (literal string, not a sweep)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return None

    # Check for bracket syntax
    if value.startswith("[") and value.endswith("]"):
        return _parse_bracket_sweep(value)

    # Check for comma-separated syntax
    if "," in value:
        return _parse_comma_sweep(value)

    # Single value - not a sweep
    return None


def _parse_bracket_sweep(value: str) -> list[Any]:
    """Parse bracket syntax sweep: [val1, val2, val3].

    :param value: String in bracket syntax.
    :return: List of parsed values.
    """
    # Remove brackets
    inner = value[1:-1].strip()

    if not inner:
        return []

    # Split by comma, respecting nested structures
    values = _split_respecting_nesting(inner)

    # Parse each value
    return [_infer_value_type(v.strip()) for v in values]


def _parse_comma_sweep(value: str) -> list[Any]:
    """Parse comma-separated sweep: val1,val2,val3.

    :param value: Comma-separated string.
    :return: List of parsed values.
    """
    # Simple split - comma-separated syntax doesn't support nesting
    values = value.split(",")
    return [_infer_value_type(v.strip()) for v in values]


def _split_respecting_nesting(s: str) -> list[str]:
    """Split a string by commas, respecting brackets and quotes.

    :param s: String to split.
    :return: List of parts.
    """
    parts = []
    current = []
    depth = 0
    in_quote = False
    quote_char = None

    for char in s:
        if char in ('"', "'") and not in_quote:
            in_quote = True
            quote_char = char
            current.append(char)
        elif char == quote_char and in_quote:
            in_quote = False
            quote_char = None
            current.append(char)
        elif char in ("[", "{", "(") and not in_quote:
            depth += 1
            current.append(char)
        elif char in ("]", "}", ")") and not in_quote:
            depth -= 1
            current.append(char)
        elif char == "," and depth == 0 and not in_quote:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)

    # Add final part
    if current:
        parts.append("".join(current))

    return parts


def _infer_value_type(raw: str) -> Any:
    """Infer the type of a string value using YAML-style rules.

    :param raw: Raw string value.
    :return: Parsed value with inferred type.
    """
    # Check for boolean
    if raw.lower() in ("true", "yes"):
        return True
    if raw.lower() in ("false", "no"):
        return False

    # Check for None
    if raw.lower() in ("none", "null", "~"):
        return None

    # Check for integer
    try:
        return int(raw)
    except ValueError:
        pass

    # Check for float
    try:
        return float(raw)
    except ValueError:
        pass

    # Default to string
    return raw


def extract_cli_multirun_overrides(
    argv: list[str],
) -> tuple[list[Override], dict[str, list[Any]], list[dict[str, Any]]]:
    """Extract multirun configuration from CLI arguments.

    Separates CLI arguments into:
    - Regular overrides (key=value without sweep syntax)
    - Sweep parameters (key=val1,val2 or key=[val1, val2])
    - Experiments (from -e/--experiment flags)

    :param argv: List of CLI arguments (typically sys.argv[1:]).
    :return: Tuple of (regular_overrides, sweep_dict, experiments_list).

    Examples::

        # Sweep syntax
        extract_cli_multirun_overrides(["lr=0.01,0.001", "model=resnet"])
        # -> ([Override(model=resnet)], {"lr": [0.01, 0.001]}, [])

        # Experiment flags
        extract_cli_multirun_overrides(["-e", "model=resnet,lr=0.01", "-e", "model=vit"])
        # -> ([], {}, [{"model": "resnet", "lr": 0.01}, {"model": "vit"}])

        # Mixed
        extract_cli_multirun_overrides(["epochs=100", "lr=0.01,0.001", "-e", "model=vit"])
        # -> ([Override(epochs=100)], {"lr": [0.01, 0.001]}, [{"model": "vit"}])
    """
    regular_overrides: list[Override] = []
    sweep_params: dict[str, list[Any]] = {}
    experiments: list[dict[str, Any]] = []

    i = 0
    while i < len(argv):
        arg = argv[i]

        # Check for experiment flag
        if arg in ("-e", "--experiment"):
            if i + 1 < len(argv):
                experiment = _parse_experiment_arg(argv[i + 1])
                if experiment:
                    experiments.append(experiment)
                i += 2
            else:
                # Missing experiment value - skip
                i += 1
            continue

        # Check for combined experiment flag (--experiment=...)
        if arg.startswith("--experiment="):
            experiment = _parse_experiment_arg(arg[len("--experiment="):])
            if experiment:
                experiments.append(experiment)
            i += 1
            continue

        if arg.startswith("-e="):
            experiment = _parse_experiment_arg(arg[3:])
            if experiment:
                experiments.append(experiment)
            i += 1
            continue

        # Skip flags that don't look like overrides
        if arg.startswith("-") and not arg.startswith("~"):
            i += 1
            continue

        # Check if it's an override with potential sweep
        if "=" in arg:
            key, _, value = arg.partition("=")

            # Try to parse as sweep
            sweep_values = parse_cli_sweep_value(value)

            if sweep_values is not None and len(sweep_values) > 1:
                # It's a sweep
                try:
                    path, _ = parse_override_key(key)
                    path_str = ".".join(str(p) for p in path)
                    sweep_params[path_str] = sweep_values
                except Exception:
                    # Invalid key syntax - skip
                    pass
            else:
                # Regular override
                override = parse_cli_arg(arg)
                if override is not None:
                    regular_overrides.append(override)
        else:
            # Not an override (no =) - might be remove operation
            override = parse_cli_arg(arg)
            if override is not None:
                regular_overrides.append(override)

        i += 1

    return regular_overrides, sweep_params, experiments


def _parse_experiment_arg(arg: str) -> dict[str, Any] | None:
    """Parse an experiment argument into an override dict.

    Experiment format: key1=val1,key2=val2,...

    :param arg: The experiment argument string.
    :return: Dict of overrides, or None if invalid.

    Examples::

        _parse_experiment_arg("model=resnet,lr=0.01")
        # {"model": "resnet", "lr": 0.01}

        _parse_experiment_arg("model=resnet")
        # {"model": "resnet"}
    """
    if not arg:
        return None

    result: dict[str, Any] = {}

    # Split by comma, but need to handle values that might contain commas
    # Strategy: split by pattern that looks like "key=" boundaries
    parts = _split_experiment_arg(arg)

    for part in parts:
        if "=" not in part:
            continue

        key, _, value = part.partition("=")
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        try:
            path, _ = parse_override_key(key)
            path_str = ".".join(str(p) for p in path)
            result[path_str] = _infer_value_type(value)
        except Exception:
            # Invalid key syntax - skip this part
            continue

    return result if result else None


def _split_experiment_arg(arg: str) -> list[str]:
    """Split experiment arg by commas between key=value pairs.

    This is tricky because values might contain commas (e.g., list values).
    We use a simple heuristic: comma followed by identifier-like pattern.

    :param arg: Experiment argument string.
    :return: List of key=value parts.
    """
    # Pattern: identifier=value, identifier=value, ...
    # Split on comma followed by word char (start of next key)
    pattern = r",(?=[a-zA-Z_+~])"
    parts = re.split(pattern, arg)
    return [p.strip() for p in parts if p.strip()]
