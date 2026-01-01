from unittest import TestCase

from rconfig._internal.singleton import Singleton


class SingletonTests(TestCase):
    @property
    def singleton_impl_class(self):
        @Singleton
        class SingletonImpl:
            variable = 10

            def a_member(self) -> int:
                return 0

        return SingletonImpl

    @property
    def singleton_impl_with_params_class(self):
        @Singleton
        class SingletonImplWithParams:
            def __init__(self, a, b, c):
                self.a = a
                self.b = b
                self.c = c

        return SingletonImplWithParams

    def test_instance_getter__BeforeInstanceIsCreated__RaiseRuntimeError(self):
        # Arrange
        singleton_class = self.singleton_impl_class

        # Act
        expected_regex = "No existing instance!"
        with self.assertRaisesRegex(expected_exception=RuntimeError, expected_regex=expected_regex):
            _ = singleton_class.instance

    def test_instance_getter__AfterDefaultInstanceIsCreated__ReturnSameInstance(self):
        # Arrange
        singleton_class = self.singleton_impl_class
        expected = singleton_class()

        # Act
        actual = singleton_class.instance

        # Assert
        self.assertIs(actual, expected)
        self.assertIsInstance(actual, singleton_class.wrapped_class)

    def test_instance_getter__AfterParameterizedInstanceIsCreated__ReturnSameInstance(self):
        # Arrange
        singleton_class = self.singleton_impl_with_params_class
        expected = singleton_class(1, 2, 3)

        # Act
        actual = singleton_class.instance

        # Assert
        self.assertIs(expected, actual)
        self.assertIsInstance(actual, singleton_class.wrapped_class)

    def test_call__BeforeInstanceExist__SetAndReturnInstance(self):
        # Arrange
        singleton_class = self.singleton_impl_class

        # Act
        actual = singleton_class()

        # Assert
        self.assertIsInstance(actual, singleton_class.wrapped_class)
        self.assertIs(actual, singleton_class._instance)

    def test_call__AfterInstanceExist__ReturnExistingInstance(self):
        # Arrange
        singleton_class = self.singleton_impl_class
        expected = singleton_class()
        assert singleton_class._instance is expected

        # Act
        actual = singleton_class()

        # Assert
        self.assertIsInstance(actual, singleton_class.wrapped_class)
        self.assertIs(actual, singleton_class._instance)
        self.assertIs(actual, expected)

    def test_call__BeforeInstanceWithParamsExist__SetAndReturnInstance(self):
        # Arrange
        singleton_class = self.singleton_impl_with_params_class

        # Act
        actual = singleton_class(1, 2, 3)

        # Assert
        self.assertIsInstance(actual, singleton_class.wrapped_class)
        self.assertIs(actual, singleton_class._instance)

    def test_call__AfterInstanceWithParamsExist__ReturnExistingInstance(self):
        # Arrange
        singleton_class = self.singleton_impl_with_params_class
        expected = singleton_class(1, 2, 3)
        assert singleton_class._instance is expected

        # Act
        actual = singleton_class(1, 2, 3)

        # Assert
        self.assertIsInstance(actual, singleton_class.wrapped_class)
        self.assertIs(actual, singleton_class._instance)
        self.assertIs(actual, expected)

        # Assert
        self.assertIsInstance(actual, singleton_class.wrapped_class)
        self.assertIs(actual, singleton_class._instance)

    def test_call__BeforeInstanceWithParamsExistButMissingParam__RaiseTypeError(self):
        # Arrange
        singleton_class = self.singleton_impl_with_params_class

        # Act
        expected_regex = r'missing \d required positional argument[s]?: '
        with self.assertRaisesRegex(expected_exception=TypeError, expected_regex=expected_regex):
            _ = singleton_class(1, 2)

    def test_call__AfterInstanceWithParamsExistButMissingParam__RaiseValueError(self):
        # Arrange
        singleton_class = self.singleton_impl_with_params_class
        expected = singleton_class(1, 2, 3)
        assert singleton_class._instance is expected

        # Act
        expected_regex = r'This singleton is already instantiated with different arguments.'
        with self.assertRaisesRegex(expected_exception=ValueError, expected_regex=expected_regex):
            _ = singleton_class(1, 2)

    def test_call__AfterInstanceWithParamsExistButDifferentParamValue__RaiseValueError(self):
        # Arrange
        singleton_class = self.singleton_impl_with_params_class
        expected = singleton_class(1, 2, 3)
        assert singleton_class._instance is expected

        # Act
        expected_regex = r'This singleton is already instantiated with different arguments.'
        with self.assertRaisesRegex(expected_exception=ValueError, expected_regex=expected_regex):
            _ = singleton_class(1, 2, 4)

    def test_getattr__StaticVariable__ReturnsVariableValue(self):
        # Arrange
        singleton_class = self.singleton_impl_class

        # Act
        actual = singleton_class.variable

        # Assert
        self.assertIs(actual, 10)

    def test_getattr__CallMemberFunction__ReturnsMemberFunctionReturnValue(self):
        # Arrange
        singleton_class = self.singleton_impl_class
        instance = singleton_class()

        # Act
        actual = instance.a_member()

        # Assert
        self.assertIs(actual, 0)

    def test_getattr__UnavailableAttribute__Raises(self):
        # Arrange
        singleton_class = self.singleton_impl_class
        instance = singleton_class()

        # Act & Assert
        expected_regex = r".* object has no attribute 'unavailable_attribute'"
        with self.assertRaisesRegex(expected_exception=AttributeError, expected_regex=expected_regex):
            _ = instance.unavailable_attribute
