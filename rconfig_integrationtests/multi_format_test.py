"""Integration tests for multi-format configuration loading."""

from dataclasses import dataclass
from pathlib import Path
from unittest import TestCase

import rconfig as rc
from rconfig.composition import ConfigComposer, clear_cache

from rconfig_unittests.fixtures import MockFileSystem, mock_filesystem


# Test dataclasses defined at module level
@dataclass
class JsonTestModel:
    name: str
    layers: int


@dataclass
class TomlTestModel:
    name: str
    learning_rate: float


class MultiFormatInstantiationTests(TestCase):
    """Tests for instantiating configs from JSON and TOML files."""

    def setUp(self):
        clear_cache()
        rc._store._known_targets.clear()
        rc.register("JsonTestModel", JsonTestModel)
        rc.register("TomlTestModel", TomlTestModel)

    def test_instantiate__JsonConfig__CreatesObject(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/model.json",
            '{"_target_": "JsonTestModel", "name": "resnet", "layers": 50}',
        )

        with mock_filesystem(fs):
            # Act
            result = rc.instantiate(Path("/configs/model.json"), cli_overrides=False)

            # Assert
            self.assertIsInstance(result, JsonTestModel)
            self.assertEqual(result.name, "resnet")
            self.assertEqual(result.layers, 50)

    def test_instantiate__TomlConfig__CreatesObject(self):
        # Arrange
        content = """_target_ = "TomlTestModel"
name = "transformer"
learning_rate = 0.001
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.toml", content)

        with mock_filesystem(fs):
            # Act
            result = rc.instantiate(Path("/configs/model.toml"), cli_overrides=False)

            # Assert
            self.assertIsInstance(result, TomlTestModel)
            self.assertEqual(result.name, "transformer")
            self.assertEqual(result.learning_rate, 0.001)


class MultiFormatCompositionTests(TestCase):
    """Tests for composing configs across YAML, JSON, and TOML formats."""

    def setUp(self):
        clear_cache()

    def test_compose__YamlReferencesJson__ResolvesCorrectly(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/main.yaml",
            "_target_: App\nmodel:\n  _ref_: ./model.json\n",
        )
        fs.add_file(
            "/configs/model.json",
            '{"name": "resnet", "layers": 50}',
        )

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer()
            result = composer.compose(Path("/configs/main.yaml"))

            # Assert
            self.assertEqual(result["model"]["name"], "resnet")
            self.assertEqual(result["model"]["layers"], 50)

    def test_compose__YamlReferencesToml__ResolvesCorrectly(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/main.yaml",
            "_target_: App\nconfig:\n  _ref_: ./settings.toml\n",
        )
        fs.add_file(
            "/configs/settings.toml",
            'host = "localhost"\nport = 8080\n',
        )

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer()
            result = composer.compose(Path("/configs/main.yaml"))

            # Assert
            self.assertEqual(result["config"]["host"], "localhost")
            self.assertEqual(result["config"]["port"], 8080)

    def test_compose__JsonReferencesYaml__ResolvesCorrectly(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/main.json",
            '{"_target_": "App", "model": {"_ref_": "./model.yaml"}}',
        )
        fs.add_file(
            "/configs/model.yaml",
            "name: transformer\nlayers: 12\n",
        )

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer()
            result = composer.compose(Path("/configs/main.json"))

            # Assert
            self.assertEqual(result["model"]["name"], "transformer")
            self.assertEqual(result["model"]["layers"], 12)

    def test_compose__TomlReferencesYaml__ResolvesCorrectly(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/main.toml",
            '_target_ = "App"\n\n[model]\n_ref_ = "./model.yaml"\n',
        )
        fs.add_file(
            "/configs/model.yaml",
            "name: gpt\nlayers: 96\n",
        )

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer()
            result = composer.compose(Path("/configs/main.toml"))

            # Assert
            self.assertEqual(result["model"]["name"], "gpt")
            self.assertEqual(result["model"]["layers"], 96)

    def test_compose__MixedFormats__ResolvesAllReferences(self):
        # Arrange
        fs = MockFileSystem("/configs")

        # Main YAML file
        fs.add_file(
            "/configs/main.yaml",
            "_target_: ComplexApp\nmodel:\n  _ref_: ./model.json\ndata:\n  _ref_: ./data.toml\n",
        )

        # JSON model config
        fs.add_file(
            "/configs/model.json",
            '{"name": "bert", "hidden_size": 768}',
        )

        # TOML data config
        fs.add_file(
            "/configs/data.toml",
            'path = "/data/corpus"\nbatch_size = 32\n',
        )

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer()
            result = composer.compose(Path("/configs/main.yaml"))

            # Assert
            self.assertEqual(result["model"]["name"], "bert")
            self.assertEqual(result["model"]["hidden_size"], 768)
            self.assertEqual(result["data"]["path"], "/data/corpus")
            self.assertEqual(result["data"]["batch_size"], 32)


class MultiFormatProvenanceTests(TestCase):
    """Tests for provenance tracking across different formats."""

    def setUp(self):
        clear_cache()

    def test_provenance__JsonFile__ShowsCorrectLineNumbers(self):
        # Arrange
        content = """{
    "_target_": "Model",
    "name": "resnet",
    "layers": 50
}"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.json", content)

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer()
            composer.compose_with_provenance(Path("/configs/model.json"))
            provenance = composer.provenance

            # Assert
            name_entry = provenance.get("name")
            self.assertIsNotNone(name_entry)
            self.assertEqual(name_entry.line, 3)

            layers_entry = provenance.get("layers")
            self.assertIsNotNone(layers_entry)
            self.assertEqual(layers_entry.line, 4)

    def test_provenance__TomlFile__ShowsCorrectLineNumbers(self):
        # Arrange
        content = """_target_ = "Model"
name = "transformer"
layers = 12
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/model.toml", content)

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer()
            composer.compose_with_provenance(Path("/configs/model.toml"))
            provenance = composer.provenance

            # Assert
            name_entry = provenance.get("name")
            self.assertIsNotNone(name_entry)
            self.assertEqual(name_entry.line, 2)

            layers_entry = provenance.get("layers")
            self.assertIsNotNone(layers_entry)
            self.assertEqual(layers_entry.line, 3)

    def test_provenance__MixedFormats__TracksOriginsAcrossFormats(self):
        # Arrange
        fs = MockFileSystem("/configs")

        # Main YAML file
        fs.add_file(
            "/configs/main.yaml",
            "_target_: App\nmodel:\n  _ref_: ./model.json\n",
        )

        # JSON model config
        fs.add_file(
            "/configs/model.json",
            '{\n    "name": "resnet",\n    "layers": 50\n}',
        )

        with mock_filesystem(fs):
            # Act
            composer = ConfigComposer()
            composer.compose_with_provenance(Path("/configs/main.yaml"))
            provenance = composer.provenance

            # Assert - model.name comes from JSON file
            name_entry = provenance.get("model.name")
            self.assertIsNotNone(name_entry)
            self.assertIn("model.json", name_entry.file)


class MultiFormatOverrideTests(TestCase):
    """Tests for overrides on JSON and TOML configs."""

    def setUp(self):
        clear_cache()

    def test_override__JsonConfig__AppliesOverrides(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/model.json",
            '{"name": "resnet", "layers": 50}',
        )

        with mock_filesystem(fs):
            # Act - use rc.to_dict which applies overrides and resolves interpolations
            result = rc.to_dict(
                Path("/configs/model.json"),
                overrides={"layers": 101},
                cli_overrides=False,
            )

            # Assert
            self.assertEqual(result["name"], "resnet")
            self.assertEqual(result["layers"], 101)

    def test_override__TomlConfig__AppliesOverrides(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/model.toml",
            'name = "transformer"\nlayers = 12\n',
        )

        with mock_filesystem(fs):
            # Act - use rc.to_dict which applies overrides and resolves interpolations
            result = rc.to_dict(
                Path("/configs/model.toml"),
                overrides={"layers": 24},
                cli_overrides=False,
            )

            # Assert
            self.assertEqual(result["name"], "transformer")
            self.assertEqual(result["layers"], 24)


class MultiFormatInterpolationTests(TestCase):
    """Tests for interpolation in JSON and TOML configs."""

    def setUp(self):
        clear_cache()

    def test_interpolation__JsonConfig__ResolvesExpressions(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/model.json",
            '{"base_lr": 0.001, "lr": "${/base_lr * 10}"}',
        )

        with mock_filesystem(fs):
            # Act - use rc.to_dict which resolves interpolations
            result = rc.to_dict(Path("/configs/model.json"), cli_overrides=False)

            # Assert
            self.assertEqual(result["base_lr"], 0.001)
            self.assertEqual(result["lr"], 0.01)

    def test_interpolation__TomlConfig__ResolvesExpressions(self):
        # Arrange
        fs = MockFileSystem("/configs")
        fs.add_file(
            "/configs/model.toml",
            'base_value = 10\ncomputed = "${/base_value * 2}"\n',
        )

        with mock_filesystem(fs):
            # Act - use rc.to_dict which resolves interpolations
            result = rc.to_dict(Path("/configs/model.toml"), cli_overrides=False)

            # Assert
            self.assertEqual(result["base_value"], 10)
            self.assertEqual(result["computed"], 20)
