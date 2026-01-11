"""Unit tests for multirun CLI parsing."""

from unittest import TestCase

from rconfig.multirun import (
    parse_cli_sweep_value,
    extract_cli_multirun_overrides,
)


class ParseCliSweepValueTests(TestCase):
    """Tests for parse_cli_sweep_value function."""

    def test_parse_cli_sweep_value__CommaSeparated__ReturnsList(self):
        # Arrange
        value = "resnet,vit,mlp"

        # Act
        result = parse_cli_sweep_value(value)

        # Assert
        self.assertEqual(result, ["resnet", "vit", "mlp"])

    def test_parse_cli_sweep_value__BracketSyntax__ReturnsList(self):
        # Arrange
        value = "[resnet, vit, mlp]"

        # Act
        result = parse_cli_sweep_value(value)

        # Assert
        self.assertEqual(result, ["resnet", "vit", "mlp"])

    def test_parse_cli_sweep_value__SingleValue__ReturnsNone(self):
        # Arrange
        value = "resnet"

        # Act
        result = parse_cli_sweep_value(value)

        # Assert
        self.assertIsNone(result)

    def test_parse_cli_sweep_value__QuotedValue__ReturnsNone(self):
        # Arrange
        value = '"resnet,vit"'

        # Act
        result = parse_cli_sweep_value(value)

        # Assert
        self.assertIsNone(result)

    def test_parse_cli_sweep_value__SingleQuotedValue__ReturnsNone(self):
        # Arrange
        value = "'resnet,vit'"

        # Act
        result = parse_cli_sweep_value(value)

        # Assert
        self.assertIsNone(result)

    def test_parse_cli_sweep_value__NumericValues__ParsedCorrectly(self):
        # Arrange
        value = "0.01,0.001,0.0001"

        # Act
        result = parse_cli_sweep_value(value)

        # Assert
        self.assertEqual(result, [0.01, 0.001, 0.0001])

    def test_parse_cli_sweep_value__BooleanValues__ParsedCorrectly(self):
        # Arrange
        value = "true,false"

        # Act
        result = parse_cli_sweep_value(value)

        # Assert
        self.assertEqual(result, [True, False])

    def test_parse_cli_sweep_value__MixedTypes__ParsedCorrectly(self):
        # Arrange
        value = "[1, 2.5, true, hello]"

        # Act
        result = parse_cli_sweep_value(value)

        # Assert
        self.assertEqual(result, [1, 2.5, True, "hello"])

    def test_parse_cli_sweep_value__IntegerValues__ParsedAsInts(self):
        # Arrange
        value = "4,8,16"

        # Act
        result = parse_cli_sweep_value(value)

        # Assert
        self.assertEqual(result, [4, 8, 16])


class ExtractCliMultirunOverridesTests(TestCase):
    """Tests for extract_cli_multirun_overrides function."""

    def test_extract_cli_multirun_overrides__MixedSweepAndRegular__SeparatesCorrectly(self):
        # Arrange
        argv = ["epochs=100", "lr=0.01,0.001", "model=resnet"]

        # Act
        regular, sweep, experiments = extract_cli_multirun_overrides(argv)

        # Assert
        self.assertEqual(len(regular), 2)  # epochs and model
        self.assertIn("lr", sweep)
        self.assertEqual(sweep["lr"], [0.01, 0.001])
        self.assertEqual(len(experiments), 0)

    def test_extract_cli_multirun_overrides__ExperimentFlag__Parsed(self):
        # Arrange
        argv = ["-e", "model=resnet,lr=0.01"]

        # Act
        regular, sweep, experiments = extract_cli_multirun_overrides(argv)

        # Assert
        self.assertEqual(len(experiments), 1)
        self.assertEqual(experiments[0]["model"], "resnet")
        self.assertEqual(experiments[0]["lr"], 0.01)

    def test_extract_cli_multirun_overrides__LongExperimentFlag__Parsed(self):
        # Arrange
        argv = ["--experiment", "model=vit"]

        # Act
        regular, sweep, experiments = extract_cli_multirun_overrides(argv)

        # Assert
        self.assertEqual(len(experiments), 1)
        self.assertEqual(experiments[0]["model"], "vit")

    def test_extract_cli_multirun_overrides__MultipleExperiments__AllParsed(self):
        # Arrange
        argv = ["-e", "model=resnet", "-e", "model=vit"]

        # Act
        regular, sweep, experiments = extract_cli_multirun_overrides(argv)

        # Assert
        self.assertEqual(len(experiments), 2)

    def test_extract_cli_multirun_overrides__BracketSweep__Parsed(self):
        # Arrange
        argv = ["model=[resnet, vit, mlp]"]

        # Act
        regular, sweep, experiments = extract_cli_multirun_overrides(argv)

        # Assert
        self.assertIn("model", sweep)
        self.assertEqual(sweep["model"], ["resnet", "vit", "mlp"])

    def test_extract_cli_multirun_overrides__SkipsFlags__NotParsed(self):
        # Arrange
        argv = ["--help", "-v", "epochs=100"]

        # Act
        regular, sweep, experiments = extract_cli_multirun_overrides(argv)

        # Assert
        self.assertEqual(len(regular), 1)
        self.assertEqual(regular[0].path, ["epochs"])

    def test_extract_cli_multirun_overrides__RemoveOperation__ParsedAsRegular(self):
        # Arrange
        argv = ["~dropout"]

        # Act
        regular, sweep, experiments = extract_cli_multirun_overrides(argv)

        # Assert
        self.assertEqual(len(regular), 1)
        self.assertEqual(regular[0].operation, "remove")

    def test_extract_cli_multirun_overrides__CombinedExperimentFlag__Parsed(self):
        # Arrange
        argv = ["--experiment=model=resnet"]

        # Act
        regular, sweep, experiments = extract_cli_multirun_overrides(argv)

        # Assert
        self.assertEqual(len(experiments), 1)
        self.assertEqual(experiments[0]["model"], "resnet")

    def test_extract_cli_multirun_overrides__EmptyArgv__ReturnsEmpty(self):
        # Arrange
        argv: list[str] = []

        # Act
        regular, sweep, experiments = extract_cli_multirun_overrides(argv)

        # Assert
        self.assertEqual(regular, [])
        self.assertEqual(sweep, {})
        self.assertEqual(experiments, [])
