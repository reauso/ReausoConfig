"""Unit tests for help integration API in rconfig module."""

import threading
from io import StringIO
from unittest import TestCase

import rconfig as rc
from rconfig.help import (
    HelpIntegration,
    FlatHelpIntegration,
    GroupedHelpIntegration,
)
from rconfig.composition import Provenance


class SetHelpIntegrationTests(TestCase):
    """Tests for rc.set_help_integration function."""

    def tearDown(self) -> None:
        # Reset to default integration after each test
        rc.set_help_integration(FlatHelpIntegration())

    def test_setHelpIntegration__ValidIntegration__SetsIntegration(self):
        """Test that set_help_integration sets the integration."""
        # Arrange
        integration = GroupedHelpIntegration()

        # Act
        rc.set_help_integration(integration)

        # Assert
        self.assertIs(rc.current_help_integration(), integration)

    def test_setHelpIntegration__None__RaisesValueError(self):
        """Test that set_help_integration raises ValueError for None."""
        # Act & Assert
        with self.assertRaises(ValueError) as ctx:
            rc.set_help_integration(None)  # type: ignore

        self.assertIn("None", str(ctx.exception))

    def test_setHelpIntegration__CustomIntegration__Works(self):
        """Test that custom HelpIntegration subclass works."""

        # Arrange
        class CustomIntegration(HelpIntegration):
            def integrate(self, provenance, config_path):
                pass

        custom = CustomIntegration()

        # Act
        rc.set_help_integration(custom)

        # Assert
        self.assertIs(rc.current_help_integration(), custom)


class CurrentHelpIntegrationTests(TestCase):
    """Tests for rc.current_help_integration function."""

    def tearDown(self) -> None:
        # Reset to default integration after each test
        rc.set_help_integration(FlatHelpIntegration())

    def test_currentHelpIntegration__Default__ReturnsFlatIntegration(self):
        """Test that default integration is FlatHelpIntegration."""
        # Act
        result = rc.current_help_integration()

        # Assert
        self.assertIsInstance(result, FlatHelpIntegration)

    def test_currentHelpIntegration__AfterSet__ReturnsSetIntegration(self):
        """Test that current_help_integration returns set integration."""
        # Arrange
        integration = GroupedHelpIntegration()
        rc.set_help_integration(integration)

        # Act
        result = rc.current_help_integration()

        # Assert
        self.assertIs(result, integration)

    def test_currentHelpIntegration__NeverNone__ReturnsIntegration(self):
        """Test that current_help_integration never returns None."""
        # Act
        result = rc.current_help_integration()

        # Assert
        self.assertIsNotNone(result)
        self.assertIsInstance(result, HelpIntegration)


class HelpIntegrationDecoratorTests(TestCase):
    """Tests for rc.help_integration decorator."""

    def tearDown(self) -> None:
        # Reset to default integration after each test
        rc.set_help_integration(FlatHelpIntegration())

    def test_helpIntegration__DecoratorApplied__SetsIntegration(self):
        """Test that @help_integration decorator sets the integration."""

        # Arrange & Act
        @rc.help_integration
        def my_integration(provenance, config_path):
            pass

        # Assert
        integration = rc.current_help_integration()
        self.assertIsNotNone(integration)

    def test_helpIntegration__DecoratorApplied__ReturnsOriginalFunction(self):
        """Test that @help_integration returns the original function."""

        # Arrange & Act
        @rc.help_integration
        def my_integration(provenance, config_path):
            pass

        # Assert
        self.assertTrue(callable(my_integration))
        self.assertEqual(my_integration.__name__, "my_integration")

    def test_helpIntegration__DecoratorFunction__CalledOnIntegrate(self):
        """Test that decorated function is called on integrate."""
        # Arrange
        call_log = []

        @rc.help_integration
        def my_integration(provenance, config_path):
            call_log.append((provenance, config_path))

        integration = rc.current_help_integration()
        provenance = Provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertEqual(len(call_log), 1)
        self.assertEqual(call_log[0][1], "config.yaml")


class ThreadSafetyTests(TestCase):
    """Tests for thread safety of help integration storage."""

    def tearDown(self) -> None:
        # Reset to default integration after each test
        rc.set_help_integration(FlatHelpIntegration())

    def test_setHelpIntegration__ConcurrentAccess__ThreadSafe(self):
        """Test that set_help_integration is thread-safe."""
        # Arrange
        errors = []
        integrations = [
            FlatHelpIntegration(),
            GroupedHelpIntegration(),
        ]

        def setter(integration):
            try:
                for _ in range(100):
                    rc.set_help_integration(integration)
            except Exception as e:
                errors.append(e)

        def getter():
            try:
                for _ in range(100):
                    result = rc.current_help_integration()
                    if result is None:
                        errors.append(ValueError("Got None"))
            except Exception as e:
                errors.append(e)

        # Act
        threads = []
        for i in range(4):
            t = threading.Thread(target=setter, args=(integrations[i % 2],))
            threads.append(t)
        for _ in range(2):
            t = threading.Thread(target=getter)
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert
        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")
