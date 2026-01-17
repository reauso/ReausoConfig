"""Unit tests for ArgparseHelpIntegration."""

import argparse
from unittest import TestCase

from rconfig.help import ArgparseHelpIntegration
from rconfig.provenance import Provenance, ProvenanceBuilder


class ArgparseHelpIntegrationTests(TestCase):
    """Tests for the ArgparseHelpIntegration class."""

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

    # === Integration Tests ===

    def test_integrate__ValidProvenance__AddsToEpilog(self):
        """Test that integrate adds config entries to parser epilog."""
        # Arrange
        parser = argparse.ArgumentParser()
        integration = ArgparseHelpIntegration(parser)
        provenance = self._create_test_provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertIsNotNone(parser.epilog)
        self.assertIn("model.lr", parser.epilog)
        self.assertIn("model.hidden_size", parser.epilog)

    def test_integrate__ValidProvenance__IncludesHeader(self):
        """Test that epilog includes configuration header."""
        # Arrange
        parser = argparse.ArgumentParser()
        integration = ArgparseHelpIntegration(parser)
        provenance = self._create_test_provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertIn("Configuration options", parser.epilog)

    def test_integrate__WithTypeHints__IncludesTypes(self):
        """Test that epilog includes type hints."""
        # Arrange
        parser = argparse.ArgumentParser()
        integration = ArgparseHelpIntegration(parser)
        provenance = self._create_test_provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertIn("float", parser.epilog)
        self.assertIn("int", parser.epilog)

    def test_integrate__WithDescriptions__IncludesDescriptions(self):
        """Test that epilog includes descriptions."""
        # Arrange
        parser = argparse.ArgumentParser()
        integration = ArgparseHelpIntegration(parser)
        provenance = self._create_test_provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertIn("Learning rate", parser.epilog)
        self.assertIn("Hidden layer size", parser.epilog)

    # === Existing Epilog Tests ===

    def test_integrate__ExistingEpilog__AppendsToExisting(self):
        """Test that integrate appends to existing epilog."""
        # Arrange
        parser = argparse.ArgumentParser(epilog="Existing epilog text")
        integration = ArgparseHelpIntegration(parser)
        provenance = self._create_test_provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertIn("Existing epilog text", parser.epilog)
        self.assertIn("model.lr", parser.epilog)

    # === consume_help_flag Tests ===

    def test_consumeHelpFlag__Default__IsFalse(self):
        """Test that consume_help_flag defaults to False for argparse."""
        # Arrange
        parser = argparse.ArgumentParser()

        # Act
        integration = ArgparseHelpIntegration(parser)

        # Assert
        self.assertFalse(integration.consume_help_flag)

    # === Does Not Exit Tests ===

    def test_integrate__Always__DoesNotExit(self):
        """Test that integrate does not call sys.exit."""
        # Arrange
        parser = argparse.ArgumentParser()
        integration = ArgparseHelpIntegration(parser)
        provenance = self._create_test_provenance()

        # Act - should not raise SystemExit
        integration.integrate(provenance, "config.yaml")

        # Assert - if we get here, no SystemExit was raised
        self.assertTrue(True)

    # === Empty Provenance Tests ===

    def test_integrate__EmptyProvenance__AddsEmptyMessage(self):
        """Test that empty provenance adds appropriate message."""
        # Arrange
        parser = argparse.ArgumentParser()
        integration = ArgparseHelpIntegration(parser)
        provenance = Provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertIsNotNone(parser.epilog)
        self.assertIn("No configuration options found", parser.epilog)

    # === Formatter Class Tests ===

    def test_integrate__SetsRawFormatter__PreservesFormatting(self):
        """Test that parser uses RawDescriptionHelpFormatter."""
        # Arrange
        parser = argparse.ArgumentParser()
        integration = ArgparseHelpIntegration(parser)
        provenance = self._create_test_provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertEqual(
            parser.formatter_class, argparse.RawDescriptionHelpFormatter
        )

    # === Edge Case Tests ===

    def test_integrate__ParserWithRawFormatter__PreservesFormatter(self):
        """Test that existing RawDescriptionHelpFormatter is preserved."""
        # Arrange
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        integration = ArgparseHelpIntegration(parser)
        provenance = self._create_test_provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertEqual(
            parser.formatter_class, argparse.RawDescriptionHelpFormatter
        )

    def test_integrate__MultipleCalls__AppendsMultipleTimes(self):
        """Test multiple integrate() calls append correctly."""
        # Arrange
        parser = argparse.ArgumentParser()
        integration = ArgparseHelpIntegration(parser)
        builder1 = ProvenanceBuilder()
        builder1.add("key1", file="config1.yaml", line=1, value=1, type_hint=int)
        prov1 = builder1.build()
        builder2 = ProvenanceBuilder()
        builder2.add("key2", file="config2.yaml", line=1, value=2, type_hint=int)
        prov2 = builder2.build()

        # Act
        integration.integrate(prov1, "config1.yaml")
        integration.integrate(prov2, "config2.yaml")

        # Assert
        self.assertIn("key1", parser.epilog)
        self.assertIn("key2", parser.epilog)
        self.assertIn("config1.yaml", parser.epilog)
        self.assertIn("config2.yaml", parser.epilog)

    def test_integrate__EmptyEpilog__SetsEpilog(self):
        """Test that empty epilog is set correctly (None -> epilog)."""
        # Arrange
        parser = argparse.ArgumentParser()
        self.assertIsNone(parser.epilog)
        integration = ArgparseHelpIntegration(parser)
        provenance = self._create_test_provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertIsNotNone(parser.epilog)
        self.assertIn("Configuration options", parser.epilog)

    def test_integrate__ParserWithDescription__PreservesDescription(self):
        """Test that parser description is preserved."""
        # Arrange
        description = "My application description"
        parser = argparse.ArgumentParser(description=description)
        integration = ArgparseHelpIntegration(parser)
        provenance = self._create_test_provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertEqual(parser.description, description)

    def test_integrate__ParserWithArguments__PreservesArguments(self):
        """Test that parser arguments are preserved."""
        # Arrange
        parser = argparse.ArgumentParser()
        parser.add_argument("--verbose", "-v", action="store_true")
        parser.add_argument("--output", "-o", type=str)
        integration = ArgparseHelpIntegration(parser)
        provenance = self._create_test_provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert - parser should still have the arguments
        # Check by parsing known args
        args = parser.parse_args(["--verbose", "-o", "test.txt"])
        self.assertTrue(args.verbose)
        self.assertEqual(args.output, "test.txt")

    def test_integrate__TypeHintInEpilog__ShowsTypes(self):
        """Test that type hints appear in the epilog."""
        # Arrange
        parser = argparse.ArgumentParser()
        integration = ArgparseHelpIntegration(parser)
        provenance = self._create_test_provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertIn("float", parser.epilog)
        self.assertIn("int", parser.epilog)

    def test_integrate__DescriptionInEpilog__ShowsDescriptions(self):
        """Test that descriptions appear in the epilog."""
        # Arrange
        parser = argparse.ArgumentParser()
        integration = ArgparseHelpIntegration(parser)
        provenance = self._create_test_provenance()

        # Act
        integration.integrate(provenance, "config.yaml")

        # Assert
        self.assertIn("Learning rate", parser.epilog)
        self.assertIn("Hidden layer size", parser.epilog)
