"""Unit tests for multirun instantiator functions."""

from unittest import TestCase

from rconfig.multirun import (
    InvalidSweepValueError,
    generate_run_configs,
    generate_sweep_combinations,
    validate_sweep_values,
    apply_ref_shorthand_to_sweep,
)
from rconfig.multirun.instantiator import validate_list_type_sweep_value


class GenerateSweepCombinationsTests(TestCase):
    """Tests for generate_sweep_combinations function."""

    def test_generate_sweep_combinations__EmptySweep__YieldsEmptyDict(self):
        # Arrange
        sweep: dict = {}

        # Act
        results = list(generate_sweep_combinations(sweep))

        # Assert
        self.assertEqual(results, [{}])

    def test_generate_sweep_combinations__SingleParam__YieldsAllValues(self):
        # Arrange
        sweep = {"lr": [0.01, 0.001, 0.0001]}

        # Act
        results = list(generate_sweep_combinations(sweep))

        # Assert
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], {"lr": 0.01})
        self.assertEqual(results[1], {"lr": 0.001})
        self.assertEqual(results[2], {"lr": 0.0001})

    def test_generate_sweep_combinations__MultipleParams__YieldsCartesianProduct(self):
        # Arrange
        sweep = {"lr": [0.01, 0.001], "layers": [4, 8]}

        # Act
        results = list(generate_sweep_combinations(sweep))

        # Assert
        self.assertEqual(len(results), 4)  # 2 x 2
        self.assertIn({"lr": 0.01, "layers": 4}, results)
        self.assertIn({"lr": 0.01, "layers": 8}, results)
        self.assertIn({"lr": 0.001, "layers": 4}, results)
        self.assertIn({"lr": 0.001, "layers": 8}, results)


class GenerateRunConfigsTests(TestCase):
    """Tests for generate_run_configs function."""

    def test_generate_run_configs__SweepOnly__GeneratesCartesianProduct(self):
        # Arrange
        sweep = {"lr": [0.01, 0.001]}

        # Act
        results = generate_run_configs(sweep=sweep)

        # Assert
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], {"lr": 0.01})
        self.assertEqual(results[1], {"lr": 0.001})

    def test_generate_run_configs__ExperimentsOnly__YieldsEachExperiment(self):
        # Arrange
        experiments = [
            {"model": "resnet", "lr": 0.01},
            {"model": "vit", "lr": 0.001},
        ]

        # Act
        results = generate_run_configs(experiments=experiments)

        # Assert
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], {"model": "resnet", "lr": 0.01})
        self.assertEqual(results[1], {"model": "vit", "lr": 0.001})

    def test_generate_run_configs__BothSweepAndExperiments__ExpandsEach(self):
        # Arrange
        experiments = [{"model": "resnet"}, {"model": "vit"}]
        sweep = {"lr": [0.01, 0.001]}

        # Act
        results = generate_run_configs(experiments=experiments, sweep=sweep)

        # Assert
        self.assertEqual(len(results), 4)  # 2 experiments x 2 lr values

    def test_generate_run_configs__WithOverrides__AppliedToAll(self):
        # Arrange
        sweep = {"lr": [0.01, 0.001]}
        overrides = {"epochs": 100}

        # Act
        results = generate_run_configs(sweep=sweep, overrides=overrides)

        # Assert
        for result in results:
            self.assertEqual(result["epochs"], 100)

    def test_generate_run_configs__SweepOverridesConstant__SweepWins(self):
        # Arrange
        sweep = {"lr": [0.01]}
        overrides = {"lr": 0.1}  # Will be overridden by sweep

        # Act
        results = generate_run_configs(sweep=sweep, overrides=overrides)

        # Assert
        self.assertEqual(results[0]["lr"], 0.01)

    def test_generate_run_configs__NoSweepNoExperiments__ReturnsOverridesOnly(self):
        # Arrange
        overrides = {"epochs": 100}

        # Act
        results = generate_run_configs(overrides=overrides)

        # Assert
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], {"epochs": 100})


class ValidateSweepValuesTests(TestCase):
    """Tests for validate_sweep_values function."""

    def test_validate_sweep_values__ValidLists__NoError(self):
        # Arrange
        sweep = {"lr": [0.01, 0.001], "layers": [4, 8, 16]}

        # Act & Assert - should not raise
        validate_sweep_values(sweep)

    def test_validate_sweep_values__NonListValue__RaisesValueError(self):
        # Arrange
        sweep = {"lr": 0.01}  # Not a list

        # Act & Assert
        with self.assertRaises(ValueError) as ctx:
            validate_sweep_values(sweep)

        self.assertIn("lr", str(ctx.exception))
        self.assertIn("must be a list", str(ctx.exception))

    def test_validate_sweep_values__EmptyDict__NoError(self):
        # Arrange
        sweep: dict = {}

        # Act & Assert - should not raise
        validate_sweep_values(sweep)


class ValidateListTypeSweepValueTests(TestCase):
    """Tests for validate_list_type_sweep_value function."""

    def test_validate_list_type_sweep_value__NonListValue__RaisesInvalidSweepValueError(self):
        # Arrange
        path = "callbacks"
        value = "single_string"
        index = 0

        # Act & Assert
        with self.assertRaises(InvalidSweepValueError) as ctx:
            validate_list_type_sweep_value(path, value, index)

        self.assertIn("callbacks", str(ctx.exception))
        self.assertIn("index 0", str(ctx.exception))

    def test_validate_list_type_sweep_value__ListValue__NoError(self):
        # Arrange
        path = "callbacks"
        value = ["logger", "checkpoint"]
        index = 0

        # Act & Assert - should not raise
        validate_list_type_sweep_value(path, value, index)


class ApplyRefShorthandToSweepTests(TestCase):
    """Tests for apply_ref_shorthand_to_sweep function."""

    def test_apply_ref_shorthand__DictField__ConvertsToRef(self):
        # Arrange
        sweep_overrides = {"model": "models/resnet"}
        config = {"model": {"_target_": "Model", "layers": 10}}

        # Act
        result = apply_ref_shorthand_to_sweep(sweep_overrides, config)

        # Assert
        self.assertIn("model._ref_", result)
        self.assertEqual(result["model._ref_"], "models/resnet")
        self.assertNotIn("model", result)

    def test_apply_ref_shorthand__ScalarField__NoConversion(self):
        # Arrange
        sweep_overrides = {"lr": "0.01"}
        config = {"lr": 0.001}  # Scalar, not dict

        # Act
        result = apply_ref_shorthand_to_sweep(sweep_overrides, config)

        # Assert
        self.assertEqual(result, {"lr": "0.01"})

    def test_apply_ref_shorthand__NonStringValue__NoConversion(self):
        # Arrange
        sweep_overrides = {"model": {"_target_": "NewModel"}}  # Dict value
        config = {"model": {"_target_": "Model"}}

        # Act
        result = apply_ref_shorthand_to_sweep(sweep_overrides, config)

        # Assert
        self.assertEqual(result, {"model": {"_target_": "NewModel"}})

    def test_apply_ref_shorthand__NestedPath__ConvertsToRef(self):
        # Arrange
        sweep_overrides = {"trainer.optimizer": "optimizers/adam"}
        config = {
            "trainer": {
                "optimizer": {"_target_": "Adam", "lr": 0.001}
            }
        }

        # Act
        result = apply_ref_shorthand_to_sweep(sweep_overrides, config)

        # Assert
        self.assertIn("trainer.optimizer._ref_", result)

    def test_apply_ref_shorthand__NonExistentPath__NoConversion(self):
        # Arrange
        sweep_overrides = {"nonexistent": "value"}
        config = {"model": {"_target_": "Model"}}

        # Act
        result = apply_ref_shorthand_to_sweep(sweep_overrides, config)

        # Assert
        self.assertEqual(result, {"nonexistent": "value"})
