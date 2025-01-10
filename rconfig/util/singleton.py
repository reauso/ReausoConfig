from typing import TypeVar, Type, Generic, Optional

_T = TypeVar('_T')


class Singleton(Generic[_T]):
    """
    A singleton decorator for classes of which a maximum of one instance should exist.
    """

    def __init__(self, wrapped_cls: Type[_T]) -> None:
        """
        Creates a new Singleton instance.

        :param wrapped_cls: The wrapped class.
        """
        super().__init__()
        self._wrapped_cls = wrapped_cls
        self._instance = None
        self._args = None
        self._kwargs = None

    @property
    def wrapped_class(self) -> Type[_T]:
        """ The wrapped class of this singleton. """
        return self._wrapped_cls

    @property
    def instance(self) -> Optional[_T]:
        """ The singleton instance of the type of the wrapped class or None if no instance has been created so far. """
        return self._instance

    @property
    def has_instance(self) -> bool:
        """ True if the singleton instance has been created already, otherwise False. """
        return self._instance is not None

    def default_instance(self) -> _T:
        """
        Create a new instance without any extra parameters if no instance exists and return it.
        Otherwise, return the existing instance.
        """
        try:
            return self.__call__()
        except ValueError:
            msg = ('This singleton instance is already instantiated with parameters and therefore can'
                   'only be accessed by the instance property of this class or another constructing call.')
            raise RuntimeError(msg)

    def __call__(self, *args, **kwargs) -> _T:
        if self._instance is None:
            self._instance = self._wrapped_cls(*args, **kwargs)
            self._args = args
            self._kwargs = kwargs

        if not args == self._args or not kwargs == self._kwargs:
            raise ValueError('This singleton is already instantiated with different arguments.')

        return self._instance
