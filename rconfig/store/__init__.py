"""Target class store and registry.

This module provides the ConfigStore singleton for registering and
looking up target classes.
"""

from .Store import ConfigStore, ConfigReference

__all__ = ["ConfigStore", "ConfigReference"]
