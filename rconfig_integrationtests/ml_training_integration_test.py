"""Comprehensive ML Training integration tests for the rconfig library.

These tests demonstrate a realistic ML training configuration that uses all
composition features: _ref_, _instance_, provenance, and overrides.
"""

from dataclasses import dataclass
from pathlib import Path
from unittest.case import TestCase

import rconfig as rc


# =============================================================================
# Dataclass definitions for the ML training example
# =============================================================================


@dataclass
class Logger:
    """Logging configuration."""

    level: str
    output_dir: str


@dataclass
class Optimizer:
    """Optimizer configuration."""

    type: str
    learning_rate: float
    weight_decay: float
    betas: list[float]


@dataclass
class Scheduler:
    """Learning rate scheduler configuration."""

    type: str
    warmup_epochs: int
    min_lr: float


@dataclass
class Augmentation:
    """Data augmentation configuration."""

    random_crop: bool = True
    horizontal_flip: bool = True


@dataclass
class Dataset:
    """Dataset configuration."""

    name: str
    root: str
    batch_size: int
    num_workers: int
    augmentation: Augmentation


@dataclass
class ModelConfig:
    """Base class for all model configurations.

    Contains shared fields that all models need: optimizer and scheduler.
    """

    optimizer: Optimizer
    scheduler: Scheduler


@dataclass
class ResNet(ModelConfig):
    """ResNet model configuration."""

    layers: int
    pretrained: bool


@dataclass
class VGG(ModelConfig):
    """VGG model configuration."""

    depth: int
    batch_norm: bool


@dataclass
class TrainingConfig:
    """Training loop configuration."""

    epochs: int
    save_every: int
    log: Logger


@dataclass
class EvalConfig:
    """Evaluation configuration."""

    metrics: list[str]
    log: Logger
    data: Dataset


@dataclass
class TrainerAppBase:
    """Base class for trainer applications.

    Contains shared fields for all trainer configurations.
    """

    logger: Logger
    dataset: Dataset
    training: TrainingConfig
    evaluation: EvalConfig


@dataclass
class TrainerApp(TrainerAppBase):
    """Main trainer application with ResNet model."""

    model: ResNet


@dataclass
class TrainerAppVGG(TrainerAppBase):
    """Main trainer application with VGG model."""

    model: VGG


@dataclass
class TrainerAppPolymorphic(TrainerAppBase):
    """Trainer application with polymorphic model field.

    Used for testing abstract type scenarios where the model
    can be any ModelConfig subclass and requires explicit _target_.
    """

    model: ModelConfig  # Abstract base - requires explicit _target_


# Path to ML training config files
ML_CONFIG_DIR = Path(__file__).parent / "config_files" / "ml_training"


class MLTrainingIntegrationTests(TestCase):
    """Integration tests for the complete ML training configuration."""

    def setUp(self):
        """Clear store and register all targets before each test."""
        rc._store._known_targets.clear()
        rc.register("trainer_app", TrainerApp)

    def tearDown(self):
        """Clear cache after each test."""
        rc.clear_cache()

    def test_validate__CompleteApp__ReturnsValid(self):
        """Validate the complete app.yaml config."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        result = rc.validate(config_path)

        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)

    def test_instantiate__CompleteApp__ReturnsCorrectTypes(self):
        """Instantiate and verify all types."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        # Verify top-level types
        self.assertIsInstance(app, TrainerApp)
        self.assertIsInstance(app.logger, Logger)
        self.assertIsInstance(app.dataset, Dataset)
        self.assertIsInstance(app.model, ResNet)
        self.assertIsInstance(app.training, TrainingConfig)
        self.assertIsInstance(app.evaluation, EvalConfig)

        # Verify nested types
        self.assertIsInstance(app.model.optimizer, Optimizer)
        self.assertIsInstance(app.model.scheduler, Scheduler)
        self.assertIsInstance(app.dataset.augmentation, Augmentation)

    def test_instantiate__SharedLogger__SameObjectInstance(self):
        """Verify training.log and evaluation.log are the same object."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        # Both training and evaluation should share the same logger instance
        self.assertIs(app.training.log, app.logger)
        self.assertIs(app.evaluation.log, app.logger)
        self.assertIs(app.training.log, app.evaluation.log)

    def test_instantiate__SharedDataset__SameObjectInstance(self):
        """Verify evaluation.data is same as top-level dataset."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        # Evaluation should share the same dataset instance
        self.assertIs(app.evaluation.data, app.dataset)

    def test_instantiate__ModelOptimizer__InheritsFromBase(self):
        """Verify optimizer comes from base with overrides."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        # Optimizer should have values from base
        self.assertEqual(app.model.optimizer.type, "adam")
        self.assertEqual(app.model.optimizer.weight_decay, 0.0001)
        self.assertEqual(app.model.optimizer.betas, [0.9, 0.999])

        # learning_rate should be overridden from 0.001 to 0.01
        self.assertEqual(app.model.optimizer.learning_rate, 0.01)

    def test_instantiate__ModelScheduler__InheritsFromBase(self):
        """Verify scheduler comes from base without overrides."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        # Scheduler should have values from base (no overrides in resnet.yaml)
        self.assertEqual(app.model.scheduler.type, "cosine")
        self.assertEqual(app.model.scheduler.warmup_epochs, 5)
        self.assertEqual(app.model.scheduler.min_lr, 0.00001)

    def test_instantiate__DatasetAugmentation__ImplicitTarget(self):
        """Verify augmentation is instantiated via implicit target inference."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        # Augmentation should be instantiated from nested config
        self.assertIsInstance(app.dataset.augmentation, Augmentation)
        self.assertTrue(app.dataset.augmentation.random_crop)
        self.assertTrue(app.dataset.augmentation.horizontal_flip)

    def test_override__BatchSize__AppliesCorrectly(self):
        """Override dataset.batch_size via API."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        app = rc.instantiate(
            config_path,
            overrides={"dataset.batch_size": 256},
            cli_overrides=False,
        )

        self.assertEqual(app.dataset.batch_size, 256)

    def test_override__Epochs__AppliesViaOverrideDict(self):
        """Override training.epochs programmatically."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        app = rc.instantiate(
            config_path,
            overrides={"training.epochs": 200},
            cli_overrides=False,
        )

        self.assertEqual(app.training.epochs, 200)

    def test_workflow__ValidateThenInstantiate__CompleteExample(self):
        """Full workflow validation then instantiation."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        # Step 1: Validate (dry-run)
        result = rc.validate(config_path)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)

        # Step 2: Instantiate
        app = rc.instantiate(config_path, cli_overrides=False)

        # Step 3: Verify complete structure
        self.assertIsInstance(app, TrainerApp)
        self.assertEqual(app.logger.level, "INFO")
        self.assertEqual(app.dataset.name, "cifar10")
        self.assertEqual(app.model.layers, 50)
        self.assertEqual(app.training.epochs, 100)
        self.assertEqual(app.evaluation.metrics, ["accuracy", "f1", "precision", "recall"])


class MLTrainingVGGTests(TestCase):
    """Integration tests for VGG model configuration."""

    def setUp(self):
        """Clear store and register all targets before each test."""
        rc._store._known_targets.clear()
        rc.register("trainer_app", TrainerAppVGG)
        rc.register("vgg", VGG)

    def tearDown(self):
        """Clear cache after each test."""
        rc.clear_cache()

    def test_instantiate__VGGModel__DifferentOptimizerSettings(self):
        """Instantiate VGG model and verify different overrides."""
        config_path = ML_CONFIG_DIR / "models" / "vgg.yaml"

        model = rc.instantiate(config_path, cli_overrides=False)

        # VGG-specific settings
        self.assertIsInstance(model, VGG)
        self.assertEqual(model.depth, 16)
        self.assertTrue(model.batch_norm)

        # Optimizer should have VGG-specific learning_rate override
        self.assertEqual(model.optimizer.type, "adam")
        self.assertEqual(model.optimizer.learning_rate, 0.005)

        # Scheduler should have VGG-specific warmup_epochs override
        self.assertEqual(model.scheduler.type, "cosine")
        self.assertEqual(model.scheduler.warmup_epochs, 10)


class MLTrainingRefCompositionTests(TestCase):
    """Tests specifically for _ref_ composition features."""

    def setUp(self):
        """Clear store and register all targets before each test."""
        rc._store._known_targets.clear()
        rc.register("trainer_app", TrainerApp)
        rc.register("resnet", ResNet)

    def tearDown(self):
        """Clear cache after each test."""
        rc.clear_cache()

    def test_ref__OptimizerFromBase__MergesCorrectly(self):
        """Verify _ref_ with deep merge for optimizer."""
        config_path = ML_CONFIG_DIR / "models" / "resnet.yaml"

        model = rc.instantiate(config_path, cli_overrides=False)

        # Base values should be preserved
        self.assertEqual(model.optimizer.type, "adam")
        self.assertEqual(model.optimizer.weight_decay, 0.0001)
        self.assertEqual(model.optimizer.betas, [0.9, 0.999])

        # Override should be applied
        self.assertEqual(model.optimizer.learning_rate, 0.01)

    def test_ref__NestedScheduler__ResolvesRelativePath(self):
        """Test ../base/scheduler.yaml resolution."""
        config_path = ML_CONFIG_DIR / "models" / "resnet.yaml"

        model = rc.instantiate(config_path, cli_overrides=False)

        # Scheduler should be loaded from ../base/scheduler.yaml
        self.assertIsInstance(model.scheduler, Scheduler)
        self.assertEqual(model.scheduler.type, "cosine")
        self.assertEqual(model.scheduler.warmup_epochs, 5)

    def test_ref__MultiLevelRef__AllResolved(self):
        """Config refs config that refs another config."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        # app.yaml refs models/resnet.yaml which refs base/optimizer.yaml
        app = rc.instantiate(config_path, cli_overrides=False)

        # All levels should be resolved
        self.assertIsInstance(app.model, ResNet)
        self.assertIsInstance(app.model.optimizer, Optimizer)
        self.assertEqual(app.model.optimizer.type, "adam")


class MLTrainingInstanceSharingTests(TestCase):
    """Tests specifically for _instance_ sharing features."""

    def setUp(self):
        """Clear store and register all targets before each test."""
        rc._store._known_targets.clear()
        rc.register("trainer_app", TrainerApp)

    def tearDown(self):
        """Clear cache after each test."""
        rc.clear_cache()

    def test_instance__LoggerShared__IdenticalObjects(self):
        """Verify logger is shared via _instance_."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        # All three references should be the exact same object
        self.assertIs(app.logger, app.training.log)
        self.assertIs(app.logger, app.evaluation.log)

    def test_instance__DatasetShared__IdenticalObjects(self):
        """Verify dataset is shared via _instance_."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        # Dataset should be shared with evaluation
        self.assertIs(app.dataset, app.evaluation.data)

    def test_instance__ModifyingSharedDoesNotAffectOthers__ImmutableDataclass(self):
        """Verify shared instances are the same object (dataclasses are immutable)."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        app = rc.instantiate(config_path, cli_overrides=False)

        # Since they're the same object, any attribute access should be identical
        self.assertEqual(app.logger.level, app.training.log.level)
        self.assertEqual(app.logger.output_dir, app.training.log.output_dir)


class MLTrainingProvenanceTests(TestCase):
    """Tests specifically for provenance tracking features."""

    def setUp(self):
        """Clear store and register all targets before each test."""
        rc._store._known_targets.clear()
        rc.register("trainer_app", TrainerApp)
        rc.register("resnet", ResNet)

    def tearDown(self):
        """Clear cache after each test."""
        rc.clear_cache()

    def test_provenance__TopLevelValue__TracksOriginFile(self):
        """Verify provenance tracks top-level values."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        prov = rc.get_provenance(config_path)

        # _target_ should come from app.yaml
        entry = prov.get("_target_")
        self.assertIsNotNone(entry)
        self.assertTrue(entry.file.endswith("app.yaml"))

    def test_provenance__RefValue__TracksSourceFile(self):
        """Values from _ref_ should track to source file."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        prov = rc.get_provenance(config_path)

        # logger.level should come from shared/logger.yaml
        entry = prov.get("logger.level")
        self.assertIsNotNone(entry)
        self.assertTrue(entry.file.endswith("logger.yaml"))

    def test_provenance__OverriddenValue__ShowsOverrodeField(self):
        """Values overridden in child config should show overrode."""
        config_path = ML_CONFIG_DIR / "models" / "resnet.yaml"

        prov = rc.get_provenance(config_path)

        # learning_rate should show it was overridden
        entry = prov.get("optimizer.learning_rate")
        self.assertIsNotNone(entry)
        # The overrode field should reference the base optimizer.yaml
        if entry.overrode:
            self.assertIn("optimizer.yaml", entry.overrode)

    def test_provenance__DeepNestedValue__TracksCorrectly(self):
        """Deep nested values should track correctly."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        prov = rc.get_provenance(config_path)

        # model.optimizer.type should trace back to base/optimizer.yaml
        entry = prov.get("model.optimizer.type")
        self.assertIsNotNone(entry)
        self.assertTrue(entry.file.endswith("optimizer.yaml"))

    def test_provenance__Print__FormatsCorrectly(self):
        """Verify provenance str output is formatted."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        prov = rc.get_provenance(config_path)

        # Should produce non-empty formatted output
        output = str(prov)
        self.assertIsInstance(output, str)
        self.assertTrue(len(output) > 0)
        # Should contain file references
        self.assertIn("app.yaml", output)

    def test_provenance__Items__IteratesAllEntries(self):
        """Verify provenance.items() iterates all entries."""
        config_path = ML_CONFIG_DIR / "app.yaml"

        prov = rc.get_provenance(config_path)

        # Should have multiple entries
        entries = list(prov.items())
        self.assertTrue(len(entries) > 0)

        # Each entry should be a tuple of (path, ProvenanceEntry)
        for path, entry in entries:
            self.assertIsInstance(path, str)
            self.assertIsNotNone(entry.file)
            self.assertIsInstance(entry.line, int)


class MLTrainingAutoRegistrationTests(TestCase):
    """Integration tests for auto-registration with file-based configs."""

    def setUp(self):
        """Clear store and register minimal targets before each test."""
        rc._store._known_targets.clear()
        # Only register the root target - rely on auto-registration for nested types

    def tearDown(self):
        """Clear cache after each test."""
        rc.clear_cache()

    # === SUCCESS CASES ===

    def test_validate__MinimalRegistration__AutoRegistersNestedTypes(self):
        """Only register root target, nested types auto-register from _ref_ files."""
        # Arrange
        rc.register("trainer_app", TrainerApp)
        config_path = ML_CONFIG_DIR / "app.yaml"

        # Act
        result = rc.validate(config_path)

        # Assert
        self.assertTrue(result.valid)
        # Verify nested types were auto-registered
        self.assertIn("resnet", rc._store._known_targets)

    def test_instantiate__FullAppMinimalRegistration__AllTypesCorrect(self):
        """Full app.yaml with minimal pre-registration still works."""
        # Arrange
        rc.register("trainer_app", TrainerApp)
        config_path = ML_CONFIG_DIR / "app.yaml"

        # Act
        app = rc.instantiate(config_path, cli_overrides=False)

        # Assert
        self.assertIsInstance(app, TrainerApp)
        self.assertIsInstance(app.model, ResNet)
        self.assertIsInstance(app.model.optimizer, Optimizer)
        self.assertIsInstance(app.model.scheduler, Scheduler)
        self.assertIsInstance(app.logger, Logger)
        self.assertIsInstance(app.dataset, Dataset)

    def test_instantiate__RefChainAutoRegistration__PreservesValues(self):
        """Auto-registered types from _ref_ chain have correct values."""
        # Arrange
        rc.register("trainer_app", TrainerApp)
        config_path = ML_CONFIG_DIR / "app.yaml"

        # Act
        app = rc.instantiate(config_path, cli_overrides=False)

        # Assert - verify values from _ref_ chain are correct
        self.assertEqual(app.model.optimizer.type, "adam")
        self.assertEqual(app.model.optimizer.learning_rate, 0.01)  # Override from resnet.yaml
        self.assertEqual(app.model.scheduler.warmup_epochs, 5)  # From base scheduler

    def test_validate__ResNetDirectly__AutoRegistersOptimizerScheduler(self):
        """Loading resnet.yaml directly auto-registers Optimizer and Scheduler."""
        # Arrange
        rc.register("resnet", ResNet)
        config_path = ML_CONFIG_DIR / "models" / "resnet.yaml"

        # Act
        result = rc.validate(config_path)

        # Assert
        self.assertTrue(result.valid)
        # Optimizer and Scheduler should be auto-registered from _ref_ files
        self.assertIn("optimizer", rc._store._known_targets)
        self.assertIn("scheduler", rc._store._known_targets)

    # === ERROR CASES ===

    def test_validate__ExplicitTargetTypeMismatch__ReturnsError(self):
        """Config with _target_ that doesn't match expected type fails."""
        # Arrange
        rc.register("trainer_app", TrainerApp)
        rc.register("logger", Logger)
        rc.register("dataset", Dataset)
        rc.register("augmentation", Augmentation)
        rc.register("trainingconfig", TrainingConfig)
        rc.register("evalconfig", EvalConfig)
        # Create a config dict with wrong _target_ for model field
        logger_config = {"_target_": "logger", "level": "INFO", "output_dir": "/tmp"}
        dataset_config = {
            "_target_": "dataset",
            "name": "cifar10",
            "root": "/data",
            "batch_size": 32,
            "num_workers": 4,
            "augmentation": {"_target_": "augmentation"},
        }
        config = {
            "_target_": "trainer_app",
            "logger": logger_config,
            "dataset": dataset_config,
            "model": {
                "_target_": "wrong_model",  # Wrong target name!
                "layers": 50,
            },
            "training": {
                "_target_": "trainingconfig",
                "epochs": 100,
                "save_every": 10,
                "log": logger_config,
            },
            "evaluation": {
                "_target_": "evalconfig",
                "metrics": ["accuracy"],
                "log": logger_config,
                "data": dataset_config,
            },
        }

        # Act
        from rconfig.errors import TargetNotFoundError

        result = rc._validator.validate(config)

        # Assert
        self.assertFalse(result.valid)
        self.assertIsInstance(result.errors[0], TargetNotFoundError)
        self.assertEqual(result.errors[0].target, "wrong_model")

    def test_validate__MissingRequiredFieldInNestedConfig__ReturnsError(self):
        """Nested config missing required fields returns proper error."""
        # Arrange
        rc.register("trainer_app", TrainerApp)
        rc.register("resnet", ResNet)
        rc.register("optimizer", Optimizer)
        rc.register("scheduler", Scheduler)
        rc.register("logger", Logger)
        rc.register("dataset", Dataset)
        rc.register("augmentation", Augmentation)
        rc.register("trainingconfig", TrainingConfig)
        rc.register("evalconfig", EvalConfig)
        from rconfig.errors import MissingFieldError

        # Config with missing 'layers' field in model
        logger_config = {"_target_": "logger", "level": "INFO", "output_dir": "/tmp"}
        dataset_config = {
            "_target_": "dataset",
            "name": "cifar10",
            "root": "/data",
            "batch_size": 32,
            "num_workers": 4,
            "augmentation": {"_target_": "augmentation"},
        }
        config = {
            "_target_": "trainer_app",
            "logger": logger_config,
            "dataset": dataset_config,
            "model": {
                "_target_": "resnet",
                # Missing 'layers' field!
                "pretrained": False,
                "optimizer": {"_target_": "optimizer", "type": "adam", "learning_rate": 0.01, "weight_decay": 0.0001, "betas": [0.9, 0.999]},
                "scheduler": {"_target_": "scheduler", "type": "cosine", "warmup_epochs": 5, "min_lr": 0.00001},
            },
            "training": {
                "_target_": "trainingconfig",
                "epochs": 100,
                "save_every": 10,
                "log": logger_config,
            },
            "evaluation": {
                "_target_": "evalconfig",
                "metrics": ["accuracy"],
                "log": logger_config,
                "data": dataset_config,
            },
        }

        # Act
        result = rc._validator.validate(config)

        # Assert
        self.assertFalse(result.valid)
        self.assertIsInstance(result.errors[0], MissingFieldError)
        self.assertEqual(result.errors[0].field, "layers")
