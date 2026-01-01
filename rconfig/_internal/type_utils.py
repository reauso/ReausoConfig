"""Shared type utilities for config validation and instantiation.

This module provides utilities for analyzing type hints, extracting class types,
and determining if types can be used as config targets.
"""

import inspect
from typing import Any, Union, get_args, get_origin

from rconfig.store import ConfigStore


# Sentinel for _target_ key
TARGET_KEY = "_target_"


def is_class_type(hint: type) -> bool:
    """Check if a type hint represents a class that could be a config target.

    Excludes primitive types and built-in collection types that cannot
    be config targets.

    :param hint: Type hint to check.
    :return: True if hint is a class type that could be a config target.
    """
    origin = get_origin(hint)

    # If it has an origin, it's a generic (list[X], dict[K, V], Optional[X], etc.)
    if origin is not None:
        return False

    # Check if it's actually a class
    if not isinstance(hint, type):
        return False

    # Exclude primitive types and built-in collections
    excluded_types = (
        int,
        float,
        str,
        bool,
        bytes,
        type(None),
        list,
        dict,
        set,
        frozenset,
        tuple,
    )
    if hint in excluded_types:
        return False

    return True


def extract_class_from_hint(hint: type) -> type | None:
    """Extract the underlying class type from a type hint.

    Handles Optional[X], Union[X, None], and plain class types.
    Returns None if the hint doesn't represent a single class type.

    :param hint: Type hint to analyze.
    :return: The underlying class type, or None if not applicable.
    """
    origin = get_origin(hint)
    args = get_args(hint)

    # Handle Optional[X] which is Union[X, None]
    if origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            # It's Optional[X], check if X is a class
            inner = non_none_args[0]
            if is_class_type(inner):
                return inner
        return None

    # Plain class type
    if is_class_type(hint):
        return hint

    return None


def could_be_implicit_nested(value: Any, expected_type: type | None) -> bool:
    """Check if value could be an implicit nested config (dict without _target_).

    A dict could be an implicit nested config if:
    1. It's a dict without _target_
    2. The expected type is a class type (not list, dict, etc.)

    :param value: The value to check.
    :param expected_type: Expected type from parent's type hint.
    :return: True if value could be an implicit nested config.
    """
    if not isinstance(value, dict):
        return False
    if TARGET_KEY in value:
        return False  # Already has _target_, not implicit
    if expected_type is None:
        return False

    # Extract the actual class type from the hint (handle Optional, etc.)
    class_type = extract_class_from_hint(expected_type)
    return class_type is not None


def find_registered_subclasses(store: ConfigStore, base_class: type) -> list[str]:
    """Find all registered targets that are subclasses of the given base class.

    :param store: ConfigStore containing registered target classes.
    :param base_class: Base class to find subclasses of.
    :return: List of target names whose classes are subclasses of base_class.
    """
    subclasses: list[str] = []

    for name, reference in store.known_references.items():
        target_class = reference.target_class
        # Check if target_class is a subclass of base_class (including exact match)
        try:
            if issubclass(target_class, base_class):
                subclasses.append(name)
        except TypeError:
            # issubclass can raise TypeError for some types
            continue

    return subclasses


def find_exact_match(store: ConfigStore, cls: type) -> str | None:
    """Find a registered target that exactly matches the given class.

    :param store: ConfigStore containing registered target classes.
    :param cls: Class to find exact match for.
    :return: Target name if exact match found, None otherwise.
    """
    for name, reference in store.known_references.items():
        if reference.target_class is cls:
            return name
    return None


def is_concrete_type(
    store: ConfigStore, cls: type
) -> tuple[bool, str | None, list[str]]:
    """Determine if a type is concrete (unambiguously instantiable).

    A type is concrete if:
    1. It is not abstract (no @abstractmethod decorators)
    2. It has exactly one registered target matching it, OR
    3. No targets are registered for this type (auto-register it)

    :param store: ConfigStore containing registered target classes.
    :param cls: Class to check.
    :return: Tuple of (is_concrete, exact_target_name, all_matching_targets)
    """
    # Check if abstract
    if inspect.isabstract(cls):
        matching = find_registered_subclasses(store, cls)
        return (False, None, matching)

    # Find all registered subclasses (including exact matches)
    matching_targets = find_registered_subclasses(store, cls)

    # Check for exact match
    exact_match = find_exact_match(store, cls)

    if exact_match is not None:
        # We have an exact match. Is it the ONLY match?
        if len(matching_targets) == 1 and matching_targets[0] == exact_match:
            # Concrete: exactly one target, it's the exact match
            return (True, exact_match, matching_targets)
        else:
            # Ambiguous: there are subclasses registered too
            return (False, None, matching_targets)
    else:
        # No exact match registered
        if len(matching_targets) == 0:
            # No subclasses registered - auto-register the class
            target_name = cls.__name__.lower()
            # Avoid name collision
            if target_name in store._known_references:
                target_name = f"{cls.__module__}.{cls.__name__}"
            store.register(target_name, cls)
            return (True, target_name, [target_name])
        else:
            # Subclasses registered but not the class itself - ambiguous
            return (False, None, matching_targets)
