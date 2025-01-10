from unittest.case import TestCase

from rconfig.util import Singleton


class SingletonTests(TestCase):
    @staticmethod
    def singleton_impl_class():
        @Singleton
        class SingletonImpl:
            pass

        return SingletonImpl

    @staticmethod
    def singleton_impl_with_params_class():
        @Singleton
        class SingletonImplWithParams:
            def __init__(self, a, b, c):
                self.a = a
                self.b = b
                self.c = c

        return SingletonImplWithParams

    def test_instance_getter__BeforeInstanceIsCreated__ReturnNone(self):
        # Arrange
        singleton_class = self.singleton_impl_class()

        # Act
        actual = singleton_class.instance

        # Assert
        self.assertIsNone(actual)

    def test_instance_getter__AfterDefaultInstanceIsCreated__ReturnSameImplInstance(self):
        # Arrange
        singleton_class = self.singleton_impl_class()
        expected = singleton_class.default_instance()

        # Act
        actual = singleton_class.instance

        # Assert
        self.assertIs(actual, expected)
        self.assertIsInstance(actual, singleton_class.wrapped_class)

    def test_instance_getter__AfterParameterizedInstanceIsCreated__ReturnSameImplInstance(self):
        # Arrange
        singleton_class = self.singleton_impl_with_params_class()
        expected = singleton_class(1, 2, 3)

        # Act
        actual = singleton_class.instance

        # Assert
        self.assertIs(expected, actual)
        self.assertIsInstance(actual, singleton_class.wrapped_class)

    def test_default_instance__BeforeInstanceExist__SetAndReturnDefaultInstance(self):
        # Arrange
        singleton_class = self.singleton_impl_class()

        # Act
        actual = singleton_class.default_instance()

        # Assert
        self.assertIsInstance(actual, singleton_class.wrapped_class)
        self.assertIs(actual, singleton_class._instance)

    def test_default_instance__AfterInstanceExist__ReturnSetInstance(self):
        # Arrange
        singleton_class = self.singleton_impl_class()
        expected = singleton_class.default_instance()
        assert singleton_class._instance is expected

        # Act
        actual = singleton_class.default_instance()

        # Assert
        self.assertIsInstance(actual, singleton_class.wrapped_class)
        self.assertIs(actual, singleton_class._instance)
        self.assertIs(actual, expected)

    def test_default_instance__BeforeInstanceWithParamsExist__RaiseTypeError(self):
        # Arrange
        singleton_class = self.singleton_impl_with_params_class()

        # Act & Assert
        expected_regex = r'missing \d required positional argument[s]?: '
        with self.assertRaisesRegex(expected_exception=TypeError, expected_regex=expected_regex):
            _ = singleton_class.default_instance()

    def test_default_instance__AfterInstanceWithParamsExist__RaiseRuntimeError(self):
        # Arrange
        singleton_class = self.singleton_impl_with_params_class()
        expected = singleton_class(1, 2, 3)
        assert singleton_class._instance is expected

        # Act & Assert
        expected_regex = (r'This singleton instance is already instantiated with parameters and therefore can'
                          r'only be accessed by the instance property of this class or another constructing call.')
        with self.assertRaisesRegex(expected_exception=RuntimeError, expected_regex=expected_regex):
            _ = singleton_class.default_instance()

    def test_call__BeforeInstanceExist__SetAndReturnInstance(self):
        # Arrange
        singleton_class = self.singleton_impl_class()

        # Act
        actual = singleton_class()

        # Assert
        self.assertIsInstance(actual, singleton_class.wrapped_class)
        self.assertIs(actual, singleton_class._instance)

    def test_call_instance__AfterInstanceExist__ReturnSetInstance(self):
        # Arrange
        singleton_class = self.singleton_impl_class()
        expected = singleton_class.default_instance()
        assert singleton_class._instance is expected

        # Act
        actual = singleton_class()

        # Assert
        self.assertIsInstance(actual, singleton_class.wrapped_class)
        self.assertIs(actual, singleton_class._instance)
        self.assertIs(actual, expected)

    def test_call__BeforeInstanceWithParamsExist__SetAndReturnInstance(self):
        # Arrange
        singleton_class = self.singleton_impl_with_params_class()

        # Act
        actual = singleton_class(1, 2, 3)

        # Assert
        self.assertIsInstance(actual, singleton_class.wrapped_class)
        self.assertIs(actual, singleton_class._instance)

    def test_call__AfterInstanceWithParamsExist__ReturnSetInstance(self):
        # Arrange
        singleton_class = self.singleton_impl_with_params_class()
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
        singleton_class = self.singleton_impl_with_params_class()

        # Act
        expected_regex = r'missing \d required positional argument[s]?: '
        with self.assertRaisesRegex(expected_exception=TypeError, expected_regex=expected_regex):
            _ = singleton_class(1, 2)

    def test_call__AfterInstanceWithParamsExistButMissingParam__RaiseValueError(self):
        # Arrange
        singleton_class = self.singleton_impl_with_params_class()
        expected = singleton_class(1, 2, 3)
        assert singleton_class._instance is expected

        # Act
        expected_regex = r'This singleton is already instantiated with different arguments.'
        with self.assertRaisesRegex(expected_exception=ValueError, expected_regex=expected_regex):
            _ = singleton_class(1, 2)

    def test_call__AfterInstanceWithParamsExistButDifferentParamValue__RaiseValueError(self):
        # Arrange
        singleton_class = self.singleton_impl_with_params_class()
        expected = singleton_class(1, 2, 3)
        assert singleton_class._instance is expected

        # Act
        expected_regex = r'This singleton is already instantiated with different arguments.'
        with self.assertRaisesRegex(expected_exception=ValueError, expected_regex=expected_regex):
            _ = singleton_class(1, 2, 4)
