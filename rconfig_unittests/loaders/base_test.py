from pathlib import Path
from typing import Any
from unittest.case import TestCase

from rconfig.loaders.base import ConfigFileLoader


class ConfigFileLoaderTests(TestCase):
    def test_ConfigFileLoader__IsAbstractClass__CannotInstantiate(self):
        # Act & Assert
        with self.assertRaises(TypeError) as context:
            ConfigFileLoader()  # type: ignore[abstract]

        self.assertIn("abstract", str(context.exception).lower())

    def test_ConfigFileLoader__ConcreteImplementation__CanInstantiate(self):
        # Arrange
        class TestLoader(ConfigFileLoader):
            def load(self, path: Path) -> dict[str, Any]:
                return {"test": "value"}

            def supports(self, path: Path) -> bool:
                return path.suffix == ".test"

        # Act
        loader = TestLoader()

        # Assert
        self.assertIsInstance(loader, ConfigFileLoader)

    def test_ConfigFileLoader__ConcreteLoad__ReturnsDict(self):
        # Arrange
        class TestLoader(ConfigFileLoader):
            def load(self, path: Path) -> dict[str, Any]:
                return {"key": "value", "number": 42}

            def supports(self, path: Path) -> bool:
                return True

        loader = TestLoader()

        # Act
        result = loader.load(Path("test.yaml"))

        # Assert
        self.assertEqual(result, {"key": "value", "number": 42})

    def test_ConfigFileLoader__ConcreteSupports__ReturnsBool(self):
        # Arrange
        class TestLoader(ConfigFileLoader):
            def load(self, path: Path) -> dict[str, Any]:
                return {}

            def supports(self, path: Path) -> bool:
                return path.suffix in (".yaml", ".yml")

        loader = TestLoader()

        # Act & Assert
        self.assertTrue(loader.supports(Path("config.yaml")))
        self.assertTrue(loader.supports(Path("config.yml")))
        self.assertFalse(loader.supports(Path("config.json")))

    def test_ConfigFileLoader__PartialImplementation__CannotInstantiate(self):
        # Arrange
        class PartialLoader(ConfigFileLoader):
            def load(self, path: Path) -> dict[str, Any]:
                return {}

            # Missing supports() method

        # Act & Assert
        with self.assertRaises(TypeError):
            PartialLoader()  # type: ignore[abstract]
