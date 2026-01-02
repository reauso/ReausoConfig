"""Partial config extraction for sub-tree instantiation.

This module provides utilities for extracting a sub-section of a composed
config and preparing instance_targets for partial instantiation.
"""

from __future__ import annotations

import copy
from typing import Any

from rconfig._internal.path_utils import get_value_at_path
from rconfig.errors import InvalidInnerPathError


def extract_partial_config(
    config: dict[str, Any],
    inner_path: str,
    instance_targets: dict[str, str | None],
) -> tuple[dict[str, Any], dict[str, str | None], set[str]]:
    """Extract a sub-config for partial instantiation.

    :param config: The fully composed and interpolation-resolved config.
    :param inner_path: Path to the section to extract (e.g., "model.encoder").
    :param instance_targets: Original instance_targets mapping from composer.
    :return: Tuple of (extracted_config, adjusted_instance_targets, external_targets).
    :raises InvalidInnerPathError: If inner_path doesn't exist or is invalid.
    """
    # Extract the sub-config at inner_path
    try:
        sub_config = get_value_at_path(config, inner_path)
    except (KeyError, IndexError, TypeError) as e:
        raise InvalidInnerPathError(inner_path, str(e))

    if not isinstance(sub_config, dict):
        raise InvalidInnerPathError(
            inner_path,
            f"Expected dict at path, got {type(sub_config).__name__}",
        )

    # Deep copy to avoid mutating original
    sub_config = copy.deepcopy(sub_config)

    # Process instance_targets for the partial scope
    processed_targets, external_targets = process_instance_targets(
        original_targets=instance_targets,
        inner_path=inner_path,
    )

    return sub_config, processed_targets, external_targets


def process_instance_targets(
    original_targets: dict[str, str | None],
    inner_path: str,
) -> tuple[dict[str, str | None], set[str]]:
    """Process instance_targets for partial instantiation.

    Handles three cases:
    1. Instance within scope, target within scope -> rebase paths
    2. Instance within scope, target outside scope -> mark as external reference
    3. Instance outside scope -> ignore (not being instantiated)

    :param original_targets: Original instance_targets from composer.
    :param inner_path: The inner path being extracted.
    :return: Tuple of (processed_targets, external_target_paths).
    """
    new_targets: dict[str, str | None] = {}
    external_targets: set[str] = set()
    inner_prefix = inner_path + "."

    for instance_path, target_path in original_targets.items():
        # Only process instances within the extracted scope
        if not _is_within_scope(instance_path, inner_path, inner_prefix):
            continue

        # Rebase instance path relative to inner_path
        rebased_instance = _rebase_path(instance_path, inner_path, inner_prefix)

        # Handle null targets
        if target_path is None:
            new_targets[rebased_instance] = None
            continue

        # Check if target is within or outside the extracted scope
        if _is_within_scope(target_path, inner_path, inner_prefix):
            # Target within scope - rebase it too
            rebased_target = _rebase_path(target_path, inner_path, inner_prefix)
            new_targets[rebased_instance] = rebased_target
        else:
            # Target outside scope - mark for external instantiation
            # Use special marker to indicate external target
            new_targets[rebased_instance] = f"__external__:{target_path}"
            external_targets.add(target_path)

    return new_targets, external_targets


def collect_external_targets(instance_targets: dict[str, str | None]) -> set[str]:
    """Find external _instance_ targets needing pre-instantiation.

    :param instance_targets: Processed instance_targets with __external__ markers.
    :return: Set of unique external target paths.
    """
    external_paths: set[str] = set()

    for target_path in instance_targets.values():
        if target_path and target_path.startswith("__external__:"):
            external_path = target_path[13:]  # Strip "__external__:" prefix
            external_paths.add(external_path)

    return external_paths


def _is_within_scope(path: str, inner_path: str, inner_prefix: str) -> bool:
    """Check if a path is within the scope of inner_path.

    :param path: The path to check.
    :param inner_path: The inner path scope.
    :param inner_prefix: Pre-computed inner_path + "." for efficiency.
    :return: True if path is exactly inner_path or starts with inner_prefix.
    """
    return path == inner_path or path.startswith(inner_prefix)


def _rebase_path(path: str, inner_path: str, inner_prefix: str) -> str:
    """Rebase a path relative to inner_path.

    :param path: The path to rebase.
    :param inner_path: The inner path to rebase relative to.
    :param inner_prefix: Pre-computed inner_path + "." for efficiency.
    :return: The rebased path (empty string if path equals inner_path).
    """
    if path == inner_path:
        return ""
    return path[len(inner_prefix) :]
