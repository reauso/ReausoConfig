"""Unit tests for HelpIntegration base class."""

from io import StringIO
from unittest import TestCase

from rconfig.help import HelpIntegration, FunctionHelpIntegration
from rconfig.provenance import Provenance, ProvenanceEntry, ProvenanceBuilder


class HelpIntegrationTests(TestCase):
    """Tests for the HelpIntegration abstract base class."""

    def _create_test_provenance(self) -> Provenance:
        """Create a test provenance object."""
        builder = ProvenanceBuilder()
        builder.add(
            "model.lr",
            file="config.yaml",
            line=1,
            value=0.001,
            type_hint=float,
            description="Learning rate",
        )
        builder.add(
            "model.hidden_size",
            file="config.yaml",
            line=2,
            value=256,
            type_hint=int,
            description="Hidden layer size",
        )
        return builder.build()

    # === consume_help_flag Property Tests ===

    def test_consumeHelpFlag__DefaultTrue__ReturnsTrue(self):
        """Test that consume_help_flag defaults to True."""

        class TestIntegration(HelpIntegration):
            def integrate(self, provenance, config_path):
                pass

        # Act
        integration = TestIntegration()

        # Assert
        self.assertTrue(integration.consume_help_flag)

    def test_consumeHelpFlag__ExplicitFalse__ReturnsFalse(self):
        """Test that consume_help_flag can be set to False."""

        class TestIntegration(HelpIntegration):
            def __init__(self):
                super().__init__(consume_help_flag=False)

            def integrate(self, provenance, config_path):
                pass

        # Act
        integration = TestIntegration()

        # Assert
        self.assertFalse(integration.consume_help_flag)

    # === Abstract Method Tests ===

    def test_integrate__NotImplemented__RaisesError(self):
        """Test that HelpIntegration cannot be instantiated directly."""
        # Act & Assert
        with self.assertRaises(TypeError) as ctx:
            HelpIntegration()

        self.assertIn("abstract", str(ctx.exception).lower())


class FunctionHelpIntegrationTests(TestCase):
    """Tests for the FunctionHelpIntegration wrapper class."""

    def _create_test_provenance(self) -> Provenance:
        """Create a test provenance object."""
        from rconfig.provenance import ProvenanceBuilder

        builder = ProvenanceBuilder()
        builder.add("test.key", file="test.yaml", line=1, value="test_value")
        return builder.build()

    # === Integration Tests ===

    def test_integrate__FunctionCalled__DelegatesToFunction(self):
        """Test that integrate() calls the wrapped function."""
        # Arrange
        call_log = []

        def test_func(provenance, config_path):
            call_log.append((provenance, config_path))

        provenance = self._create_test_provenance()
        integration = FunctionHelpIntegration(test_func)

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertEqual(len(call_log), 1)
        self.assertEqual(call_log[0][0], provenance)
        self.assertEqual(call_log[0][1], "config.yaml")

    def test_integrate__FunctionRaisesException__Propagates(self):
        """Test that exceptions from the function propagate."""
        # Arrange
        def error_func(provenance, config_path):
            raise ValueError("Test error")

        provenance = self._create_test_provenance()
        integration = FunctionHelpIntegration(error_func)

        # Act & Assert
        with self.assertRaises(ValueError) as ctx:
            integration.integrate(provenance, "config.yaml")

        self.assertEqual(str(ctx.exception), "Test error")

    # === consume_help_flag Tests ===

    def test_consumeHelpFlag__FunctionIntegration__DefaultsToTrue(self):
        """Test that FunctionHelpIntegration defaults to consume_help_flag=True."""
        # Arrange
        def test_func(provenance, config_path):
            pass

        # Act
        integration = FunctionHelpIntegration(test_func)

        # Assert
        self.assertTrue(integration.consume_help_flag)

    # === Function Attribute Preservation Tests ===

    def test_functionIntegration__FunctionName__Preserved(self):
        """Test that wrapped function's __name__ can be accessed."""
        # Arrange
        def my_custom_function(provenance, config_path):
            """Custom docstring."""
            pass

        # Act
        integration = FunctionHelpIntegration(my_custom_function)

        # Assert
        self.assertEqual(integration._func.__name__, "my_custom_function")
        self.assertEqual(integration._func.__doc__, "Custom docstring.")

    def test_functionIntegration__FunctionReturnsValue__Ignored(self):
        """Test that return value from function is ignored."""
        # Arrange
        def func_with_return(provenance, config_path):
            return "some value"

        provenance = self._create_test_provenance()
        integration = FunctionHelpIntegration(func_with_return)

        # Act
        result = integration.integrate(provenance, "config.yaml")

        # Assert - integrate returns None regardless of function return
        self.assertIsNone(result)

    def test_functionIntegration__FunctionRaisesSystemExit__Propagates(self):
        """Test that SystemExit from function propagates correctly."""
        # Arrange
        def exit_func(provenance, config_path):
            import sys
            sys.exit(0)

        provenance = self._create_test_provenance()
        integration = FunctionHelpIntegration(exit_func)

        # Act & Assert
        with self.assertRaises(SystemExit) as ctx:
            integration.integrate(provenance, "config.yaml")

        self.assertEqual(ctx.exception.code, 0)

    def test_functionIntegration__FunctionRaisesKeyboardInterrupt__Propagates(self):
        """Test that KeyboardInterrupt from function propagates correctly."""
        # Arrange
        def interrupt_func(provenance, config_path):
            raise KeyboardInterrupt()

        provenance = self._create_test_provenance()
        integration = FunctionHelpIntegration(interrupt_func)

        # Act & Assert
        with self.assertRaises(KeyboardInterrupt):
            integration.integrate(provenance, "config.yaml")

    def test_functionIntegration__LambdaFunction__Works(self):
        """Test that lambda functions work as integration handlers."""
        # Arrange
        call_count = [0]
        integration = FunctionHelpIntegration(
            lambda prov, path: call_count.__setitem__(0, call_count[0] + 1)
        )
        provenance = self._create_test_provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertEqual(call_count[0], 1)
