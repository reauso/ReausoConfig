"""Configuration instantiation subsystem.

Creates Python objects from validated config dictionaries.
"""

from .Instantiator import ConfigInstantiator
from .LazyProxy import (
    get_lazy_proxy_class,
    is_lazy_proxy,
    force_initialize,
    clear_proxy_cache,
)

__all__ = [
    "ConfigInstantiator",
    "get_lazy_proxy_class",
    "is_lazy_proxy",
    "force_initialize",
    "clear_proxy_cache",
]
