import inspect
from collections import OrderedDict
from dataclasses import dataclass, field
from inspect import Parameter
from types import MappingProxyType
from typing import Type, Any

from .util import Singleton


@dataclass(kw_only=True, frozen=True)
class ConfigReference:
    name: str
    target_class: type[Any]
    decisive_init_parameters: MappingProxyType[str, Parameter] = field(init=False, repr=True, compare=False)

    def __post_init__(self) -> None:
        self._determine_decisive_init_parameters()

    def _determine_decisive_init_parameters(self) -> None:
        self._validate_target_has_init_method()

        init_signature = inspect.signature(self.target_class.__init__, follow_wrapped=True)
        init_parameters = OrderedDict({key: value for key, value in init_signature.parameters.items() if key != 'self'})

        object.__setattr__(self, "decisive_init_parameters", MappingProxyType(init_parameters))

    def _validate_target_has_init_method(self):
        if not hasattr(self.target_class, '__init__'):
            message = (f"The class '{self.target_class.__module__}.{self.target_class.__qualname__}' "
                       f"has no '__init__' method.")
            raise AttributeError(message)


@Singleton
class ConfigStore:
    def __init__(self) -> None:
        self._known_references: dict[str, ConfigReference] = {}

    def register(
            self,
            name: str,
            target: Type[Any],
    ) -> None:
        reference = ConfigReference(
            name=name,
            target_class=target,
        )
        self._known_references[reference.name] = reference

    @property
    def known_references(self) -> MappingProxyType[str, ConfigReference]:
        return MappingProxyType(self._known_references)
