"""Type inference for partial instantiation.

This module provides utilities for inferring target types from parent's
type hints when using inner_path for partial instantiation.
"""

from typing import Any, get_args, get_origin, get_type_hints

from rconfig._internal.path_utils import (
    navigate_path,
    parse_path_segments,
    PathNavigationError,
)
from rconfig._internal.type_utils import (
    TARGET_KEY,
    extract_class_from_hint,
    is_concrete_type,
)
from rconfig.target import TargetRegistry


def infer_target_from_parent(
    config: dict[str, Any],
    path: str,
    store: TargetRegistry,
) -> str | None:
    """Infer target name from parent's type hint.

    When extracting a nested path like "model.database", this function
    checks if the parent config ("model") has a `_target_` and whether
    that target's class has a concrete type hint for the field ("database").

    Also supports list element inference for paths like "trainer.callbacks[0]"
    by extracting the element type from `list[X]` type hints.

    :param config: Full config dict (before extraction).
    :param path: Dot-notation path to the section being extracted.
    :param store: TargetRegistry with registered targets.
    :return: Inferred target name, or None if cannot infer.
    """
    # Parse path into segments
    segments = parse_path_segments(path)

    if len(segments) < 2:
        return None  # No parent to infer from (root level)

    # The final segment is the field we want to infer type for
    field_segment = segments[-1]

    # Handle list index inference (e.g., "callbacks[0]")
    if isinstance(field_segment, int):
        return _infer_list_element_type(config, segments, store)

    field_name: str = field_segment

    # Get the parent config (all segments except the last)
    parent_segments = segments[:-1]

    try:
        parent_config = navigate_path(config, parent_segments)
    except PathNavigationError:
        return None

    if not isinstance(parent_config, dict):
        return None

    if TARGET_KEY not in parent_config:
        return None

    # Get parent's target class
    parent_target = parent_config[TARGET_KEY]
    if parent_target not in store.known_targets:
        return None

    parent_class = store.known_targets[parent_target].target_class

    # Get type hint for the field
    try:
        type_hints = get_type_hints(parent_class)
    except Exception:
        return None

    field_type = type_hints.get(field_name)
    if field_type is None:
        return None

    # Extract the class from the type hint (handles Optional, etc.)
    class_type = extract_class_from_hint(field_type)
    if class_type is None:
        return None

    # Check if type is concrete (can be unambiguously instantiated)
    is_concrete, target_name, _ = is_concrete_type(store, class_type)
    if is_concrete and target_name:
        return target_name

    return None


def _infer_list_element_type(
    config: dict[str, Any],
    segments: list[str | int],
    store: TargetRegistry,
) -> str | None:
    """Infer target name for a list element from the list's type hint.

    For a path like ["trainer", "callbacks", 0], this looks at the "trainer"
    config's _target_ class, gets the type hint for "callbacks" (e.g., list[Callback]),
    and extracts the element type (Callback).

    :param config: Full config dict.
    :param segments: Parsed path segments where the last is an int (list index).
    :param store: TargetRegistry with registered targets.
    :return: Inferred target name, or None if cannot infer.
    """
    # Need at least 3 segments: grandparent, list_field, index
    # e.g., ["trainer", "callbacks", 0]
    if len(segments) < 3:
        # Path like ["callbacks", 0] - no grandparent to get type hint from
        return None

    # Find the list field name (segment before the index)
    list_field_segment = segments[-2]
    if isinstance(list_field_segment, int):
        # Nested list indices not supported (e.g., callbacks[0][1])
        return None

    list_field_name: str = list_field_segment

    # Get the grandparent config (segments before the list field)
    grandparent_segments = segments[:-2]

    try:
        if grandparent_segments:
            grandparent_config = navigate_path(config, grandparent_segments)
        else:
            grandparent_config = config
    except PathNavigationError:
        return None

    if not isinstance(grandparent_config, dict):
        return None

    if TARGET_KEY not in grandparent_config:
        return None

    # Get grandparent's target class
    grandparent_target = grandparent_config[TARGET_KEY]
    if grandparent_target not in store.known_targets:
        return None

    grandparent_class = store.known_targets[grandparent_target].target_class

    # Get type hint for the list field
    try:
        type_hints = get_type_hints(grandparent_class)
    except Exception:
        return None

    list_type = type_hints.get(list_field_name)
    if list_type is None:
        return None

    # Extract element type from list[X]
    origin = get_origin(list_type)
    if origin is not list:
        return None

    args = get_args(list_type)
    if not args:
        return None  # Unparameterized list

    element_type = args[0]

    # Extract the class from the element type (handles Optional, etc.)
    class_type = extract_class_from_hint(element_type)
    if class_type is None:
        return None

    # Check if type is concrete
    is_concrete, target_name, _ = is_concrete_type(store, class_type)
    if is_concrete and target_name:
        return target_name

    return None
