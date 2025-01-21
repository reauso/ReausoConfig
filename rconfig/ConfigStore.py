from dataclasses import dataclass
from typing import Type

from .util import Singleton


@Singleton
class ConfigStore:
    def __init__(self) -> None:
        # TODO doc
        # TODO implement
        # TODO test
        self._configs = {}

    def register(
            self,
            name: str,
            target: Type[dataclass],
    ) -> None:
        # TODO doc
        # TODO implement
        # TODO test
        pass
