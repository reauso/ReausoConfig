"""Internal utilities for rconfig.

This module contains implementation details not meant for public use.
The API may change without notice.
"""

from .singleton import Singleton
from .path_utils import (
    build_child_path,
    get_value_at_path,
    navigate_path,
    parse_path_segments,
    PathNavigationError,
)

# Note: type_utils is not imported here to avoid circular imports.
# Import directly from rconfig._internal.type_utils when needed.
