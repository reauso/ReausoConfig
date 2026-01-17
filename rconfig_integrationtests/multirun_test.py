"""Integration tests for multirun functionality.

These tests verify instantiate_multirun works end-to-end with real configs.
"""

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from types import MappingProxyType
from unittest.case import TestCase
from unittest.mock import patch

import rconfig as rc
from rconfig.help import FlatHelpIntegration
from rconfig.multirun import (
    MultirunIterator,
    MultirunResult,
    NoRunConfigurationError,
)


# Test dataclasses
@dataclass
class ModelConfig:
    hidden_size: int
    dropout: float = 0.1


@dataclass
class TrainerConfig:
    model: ModelConfig
    epochs: int
    learning_rate: float = 0.001


# Path to config files directory
CONFIG_DIR = Path(__file__).parent / "config_files"


class MultirunCoreTests(TestCase):
    """Core instantiate_multirun functionality tests."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_instantiate_multirun__SweepOnly__GeneratesCartesianProduct(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": [0.01, 0.001]}

        # Act
        results = list(rc.instantiate_multirun(
            path=config_path,
            sweep=sweep,
            cli_overrides=False,
        ))

        # Assert
        self.assertEqual(len(results), 2)
        learning_rates = [r.instance.learning_rate for r in results]
        self.assertIn(0.01, learning_rates)
        self.assertIn(0.001, learning_rates)

    def test_instantiate_multirun__ExperimentsOnly__GeneratesEachExperiment(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        experiments = [
            {"learning_rate": 0.01, "epochs": 5},
            {"learning_rate": 0.001, "epochs": 10},
        ]

        # Act
        results = list(rc.instantiate_multirun(
            path=config_path,
            experiments=experiments,
            cli_overrides=False,
        ))

        # Assert
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].instance.learning_rate, 0.01)
        self.assertEqual(results[0].instance.epochs, 5)
        self.assertEqual(results[1].instance.learning_rate, 0.001)
        self.assertEqual(results[1].instance.epochs, 10)

    def test_instantiate_multirun__BothSweepAndExperiments__ExpandsEach(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        experiments = [{"epochs": 5}, {"epochs": 10}]
        sweep = {"learning_rate": [0.01, 0.001]}

        # Act
        results = list(rc.instantiate_multirun(
            path=config_path,
            experiments=experiments,
            sweep=sweep,
            cli_overrides=False,
        ))

        # Assert
        self.assertEqual(len(results), 4)  # 2 experiments x 2 lr values

    def test_instantiate_multirun__WithConstantOverrides__AppliedToAll(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": [0.01, 0.001]}
        overrides = {"epochs": 100}

        # Act
        results = list(rc.instantiate_multirun(
            path=config_path,
            sweep=sweep,
            overrides=overrides,
            cli_overrides=False,
        ))

        # Assert
        for result in results:
            self.assertEqual(result.instance.epochs, 100)

    def test_instantiate_multirun__ExperimentOverridesConstant__ExperimentWins(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        experiments = [{"epochs": 20}]
        overrides = {"epochs": 100}

        # Act
        results = list(rc.instantiate_multirun(
            path=config_path,
            experiments=experiments,
            overrides=overrides,
            cli_overrides=False,
        ))

        # Assert
        self.assertEqual(results[0].instance.epochs, 20)

    def test_instantiate_multirun__ResultOverridesField__ContainsRunOverrides(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": [0.01]}
        overrides = {"epochs": 50}

        # Act
        results = list(rc.instantiate_multirun(
            path=config_path,
            sweep=sweep,
            overrides=overrides,
            cli_overrides=False,
        ))

        # Assert
        self.assertIsInstance(results[0].overrides, MappingProxyType)
        self.assertIn("learning_rate", results[0].overrides)
        self.assertIn("epochs", results[0].overrides)


class MultirunIteratorFeatureTests(TestCase):
    """Tests for MultirunIterator features."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_instantiate_multirun__ReturnsMultirunIterator(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": [0.01]}

        # Act
        results = rc.instantiate_multirun(
            path=config_path,
            sweep=sweep,
            cli_overrides=False,
        )

        # Assert
        self.assertIsInstance(results, MultirunIterator)

    def test_instantiate_multirun__IteratorLen__MatchesRunCount(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": [0.01, 0.001, 0.0001]}

        # Act
        results = rc.instantiate_multirun(
            path=config_path,
            sweep=sweep,
            cli_overrides=False,
        )

        # Assert
        self.assertEqual(len(results), 3)

    def test_instantiate_multirun__IteratorSlice__LazySubset(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": [0.01, 0.001, 0.0001, 0.00001]}

        # Act
        results = rc.instantiate_multirun(
            path=config_path,
            sweep=sweep,
            cli_overrides=False,
        )
        sliced = results[1:3]

        # Assert
        self.assertIsInstance(sliced, MultirunIterator)
        self.assertEqual(len(sliced), 2)

    def test_instantiate_multirun__IteratorReversed__ReverseOrder(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": [0.01, 0.001, 0.0001]}

        # Act
        results = rc.instantiate_multirun(
            path=config_path,
            sweep=sweep,
            cli_overrides=False,
        )
        reversed_results = list(reversed(results))

        # Assert
        self.assertEqual(reversed_results[0].instance.learning_rate, 0.0001)
        self.assertEqual(reversed_results[2].instance.learning_rate, 0.01)

    def test_instantiate_multirun__IteratorIndex__SingleRun(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": [0.01, 0.001, 0.0001]}

        # Act
        results = rc.instantiate_multirun(
            path=config_path,
            sweep=sweep,
            cli_overrides=False,
        )
        single = results[1]

        # Assert
        self.assertIsInstance(single, MultirunResult)
        self.assertEqual(single.instance.learning_rate, 0.001)


class MultirunErrorHandlingTests(TestCase):
    """Tests for error handling in instantiate_multirun."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_instantiate_multirun__NoSweepOrExperiments__RaisesNoRunConfigurationError(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act & Assert
        with self.assertRaises(NoRunConfigurationError):
            rc.instantiate_multirun(
                path=config_path,
                cli_overrides=False,
            )

    def test_instantiate_multirun__EmptySweepDict__RaisesNoRunConfigurationError(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act & Assert
        with self.assertRaises(NoRunConfigurationError):
            rc.instantiate_multirun(
                path=config_path,
                sweep={},
                cli_overrides=False,
            )

    def test_instantiate_multirun__InvalidSweepValue__RaisesValueError(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": 0.01}  # Not a list

        # Act & Assert
        with self.assertRaises(ValueError):
            rc.instantiate_multirun(
                path=config_path,
                sweep=sweep,  # type: ignore
                cli_overrides=False,
            )

    def test_instantiate_multirun__TryExceptPattern__CatchesError(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"nonexistent_field": [1, 2, 3]}

        # Act
        results = rc.instantiate_multirun(
            path=config_path,
            sweep=sweep,
            cli_overrides=False,
        )

        # Assert - errors are stored and raised on instance access
        errors_caught = 0
        for result in results:
            try:
                _ = result.instance
            except Exception:
                errors_caught += 1

        self.assertEqual(errors_caught, 3)


class MultirunExportTests(TestCase):
    """Tests for to_file/to_files with MultirunResult."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)
        self._temp_files: list[Path] = []

    def tearDown(self):
        for f in self._temp_files:
            if f.exists():
                f.unlink()

    def test_to_file__FromMultirunResult__ExportsConfig(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": [0.01]}

        results = list(rc.instantiate_multirun(
            path=config_path,
            sweep=sweep,
            cli_overrides=False,
        ))

        output_path = CONFIG_DIR / "test_output.yaml"
        self._temp_files.append(output_path)

        # Act
        rc.to_file(results[0], output_path)

        # Assert
        self.assertTrue(output_path.exists())


class MultirunLazyModeTests(TestCase):
    """Tests for lazy instantiation mode."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_instantiate_multirun__LazyMode__ProxiesReturned(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": [0.01]}

        # Act
        results = list(rc.instantiate_multirun(
            path=config_path,
            sweep=sweep,
            lazy=True,
            cli_overrides=False,
        ))

        # Assert - lazy proxies delay initialization
        result = results[0]
        # Accessing instance should work
        self.assertIsNotNone(result.instance)


class MultirunConfigImmutabilityTests(TestCase):
    """Tests for config immutability."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_instantiate_multirun__ResultConfig__IsImmutable(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": [0.01]}

        # Act
        results = list(rc.instantiate_multirun(
            path=config_path,
            sweep=sweep,
            cli_overrides=False,
        ))

        # Assert
        self.assertIsInstance(results[0].config, MappingProxyType)
        with self.assertRaises(TypeError):
            results[0].config["new_key"] = "value"  # type: ignore


class MultirunCLIIntegrationTests(TestCase):
    """Tests for CLI integration with instantiate_multirun."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_instantiate_multirun__CLIOverrides__WinOnConflict(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": [0.01, 0.001]}

        # Act - CLI override should win over sweep values
        with patch("sys.argv", ["prog", "epochs=999"]):
            results = list(rc.instantiate_multirun(
                path=config_path,
                sweep=sweep,
                cli_overrides=True,
            ))

        # Assert - all results should have CLI-overridden epochs
        for result in results:
            self.assertEqual(result.instance.epochs, 999)

    def test_instantiate_multirun__CLISweepSyntax__CommaSeparated(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act - comma-separated values create sweep
        with patch("sys.argv", ["prog", "learning_rate=0.01,0.001"]):
            results = list(rc.instantiate_multirun(
                path=config_path,
                cli_overrides=True,
            ))

        # Assert
        self.assertEqual(len(results), 2)
        learning_rates = [r.instance.learning_rate for r in results]
        self.assertIn(0.01, learning_rates)
        self.assertIn(0.001, learning_rates)

    def test_instantiate_multirun__CLISweepSyntax__BracketNotation(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act - bracket syntax for sweep
        with patch("sys.argv", ["prog", "learning_rate=[0.01, 0.001]"]):
            results = list(rc.instantiate_multirun(
                path=config_path,
                cli_overrides=True,
            ))

        # Assert
        self.assertEqual(len(results), 2)
        learning_rates = [r.instance.learning_rate for r in results]
        self.assertIn(0.01, learning_rates)
        self.assertIn(0.001, learning_rates)

    def test_instantiate_multirun__CLIExperimentFlag__ShortForm(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act - short form -e flag
        with patch("sys.argv", ["prog", "-e", "epochs=5", "-e", "epochs=10"]):
            results = list(rc.instantiate_multirun(
                path=config_path,
                cli_overrides=True,
            ))

        # Assert
        self.assertEqual(len(results), 2)
        epochs = [r.instance.epochs for r in results]
        self.assertIn(5, epochs)
        self.assertIn(10, epochs)

    def test_instantiate_multirun__CLIExperimentFlag__LongForm(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act - long form --experiment flag
        with patch("sys.argv", ["prog", "--experiment", "epochs=5", "--experiment", "epochs=10"]):
            results = list(rc.instantiate_multirun(
                path=config_path,
                cli_overrides=True,
            ))

        # Assert
        self.assertEqual(len(results), 2)
        epochs = [r.instance.epochs for r in results]
        self.assertIn(5, epochs)
        self.assertIn(10, epochs)

    def test_instantiate_multirun__CLIExperimentWithSweep__Combined(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"

        # Act - combine experiments with sweep
        with patch("sys.argv", ["prog", "-e", "epochs=5", "-e", "epochs=10", "learning_rate=0.01,0.001"]):
            results = list(rc.instantiate_multirun(
                path=config_path,
                cli_overrides=True,
            ))

        # Assert - 2 experiments x 2 learning rates = 4 runs
        self.assertEqual(len(results), 4)


class MultirunHelpIntegrationTests(TestCase):
    """Tests for help integration with multirun."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_help_integration__IncludesMultirunHelp(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        output = StringIO()
        integration = FlatHelpIntegration(output=output)

        # Act - trigger help display
        prov = rc.get_provenance(config_path)
        with self.assertRaises(SystemExit):
            integration.integrate(prov, str(config_path))

        # Assert - multirun help text should be included
        result = output.getvalue()
        self.assertIn("Multirun Options", result)
        self.assertIn("-e, --experiment", result)
        self.assertIn("Sweep Syntax", result)
        self.assertIn("KEY=VAL1,VAL2", result)


class MultirunAdditionalCoreTests(TestCase):
    """Additional core functionality tests."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_instantiate_multirun__ExpectedType__TypedResults(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": [0.01, 0.001]}

        # Act
        results = list(rc.instantiate_multirun(
            path=config_path,
            expected_type=TrainerConfig,
            sweep=sweep,
            cli_overrides=False,
        ))

        # Assert - instances should be of expected type
        for result in results:
            self.assertIsInstance(result.instance, TrainerConfig)


class MultirunAdditionalErrorTests(TestCase):
    """Additional error handling tests."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)

    def test_instantiate_multirun__InvalidOverridePath__ErrorOnInstanceAccess(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"nonexistent.path": [1, 2]}

        # Act
        results = rc.instantiate_multirun(
            path=config_path,
            sweep=sweep,
            cli_overrides=False,
        )

        # Assert - error should be raised on instance access
        for result in results:
            with self.assertRaises(Exception):
                _ = result.instance


class MultirunAdditionalExportTests(TestCase):
    """Additional export tests."""

    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("model", ModelConfig)
        rc.register("trainer", TrainerConfig)
        self._temp_files: list[Path] = []
        self._temp_dirs: list[Path] = []

    def tearDown(self):
        for f in self._temp_files:
            if f.exists():
                f.unlink()
        for d in self._temp_dirs:
            if d.exists():
                import shutil
                shutil.rmtree(d, ignore_errors=True)

    def test_to_files__FromMultirunResult__ExportsConfig(self):
        # Arrange
        config_path = CONFIG_DIR / "trainer_config.yaml"
        sweep = {"learning_rate": [0.01]}

        results = list(rc.instantiate_multirun(
            path=config_path,
            sweep=sweep,
            cli_overrides=False,
        ))

        output_dir = CONFIG_DIR / "test_output_dir"
        output_dir.mkdir(exist_ok=True)
        self._temp_dirs.append(output_dir)
        output_path = output_dir / "config.yaml"

        # Act
        rc.to_files(results[0], output_path)

        # Assert
        self.assertTrue(output_path.exists())
