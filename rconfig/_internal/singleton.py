from typing import TypeVar, Generic

T = TypeVar('T')


class Singleton(Generic[T]):
    """
    A singleton decorator for classes of which a maximum of one instance should exist.
    """

    def __init__(self, wrapped_cls: type[T]) -> None:
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
    def wrapped_class(self) -> type[T]:
        """ The wrapped class of this singleton. """
        return self._wrapped_cls

    @property
    def instance(self) -> T | None:
        """ The singleton instance of the type of the wrapped class or None if no instance has been created so far. """
        if not self.exists:
            message = f"No existing instance!"
            raise RuntimeError(message)

        return self._instance

    @property
    def exists(self) -> bool:
        """ True if the singleton instance has been created already, otherwise False. """
        return self._instance is not None

    def __call__(self, *args, **kwargs) -> T:
        if not self.exists:
            self._instance = self._wrapped_cls(*args, **kwargs)
            self._args = args
            self._kwargs = kwargs

        if not args == self._args or not kwargs == self._kwargs:
            raise ValueError('This singleton is already instantiated with different arguments.')

        return self._instance

    def __getattr__(self, name: str):
        """
        Delegate attribute access to the wrapped class if the attribute is not found
        on the Singleton itself.

        This allows static methods (and other class-level attributes) to be accessed
        directly via the singleton decorator instance.
        """
        return getattr(self._wrapped_cls, name)
