"""Unit tests for DependencyAnalyzer."""

import unittest

from rconfig.composition.DependencyAnalyzer import DependencyAnalyzer


class DependencyAnalyzerAnalyzeSubtreeTests(unittest.TestCase):
    """Tests for DependencyAnalyzer.analyze_subtree method."""

    def setUp(self) -> None:
        self.analyzer = DependencyAnalyzer()

    def test_analyze_subtree__NoInterpolations__ReturnsEmptySet(self):
        # Arrange
        config = {
            "model": {
                "layers": 50,
                "lr": 0.001,
            }
        }

        # Act
        result = self.analyzer.analyze_subtree(config, "model")

        # Assert
        self.assertEqual(set(), result)

    def test_analyze_subtree__AbsoluteInterpolation__ReturnsPath(self):
        # Arrange
        config = {
            "defaults": {"lr": 0.01},
            "model": {
                "learning_rate": "${/defaults.lr}",
            },
        }

        # Act
        result = self.analyzer.analyze_subtree(config, "model")

        # Assert
        self.assertEqual({"defaults.lr"}, result)

    def test_analyze_subtree__RelativeInterpolation__ReturnsAbsolutePath(self):
        # Arrange
        # Use ../lr to reference parent level (training.lr)
        # ./lr from training.model.scale resolves to training.model.lr (sibling)
        config = {
            "training": {
                "lr": 0.01,  # External to training.model
                "model": {
                    "scale": "${/training.lr}",  # Absolute reference to parent
                },
            },
        }

        # Act
        result = self.analyzer.analyze_subtree(config, "training.model")

        # Assert
        # /training.lr is external to training.model subtree
        self.assertIn("training.lr", result)

    def test_analyze_subtree__SimplePathInterpolation__ReturnsPath(self):
        # Arrange
        config = {
            "defaults": {"lr": 0.01},
            "model": {
                "learning_rate": "${defaults.lr}",
            },
        }

        # Act
        result = self.analyzer.analyze_subtree(config, "model")

        # Assert
        self.assertEqual({"defaults.lr"}, result)

    def test_analyze_subtree__InstanceRef__ReturnsTargetPath(self):
        # Arrange
        config = {
            "shared": {"database": {"url": "postgres://"}},
            "service": {
                "_instance_": "/shared.database",
            },
        }

        # Act
        result = self.analyzer.analyze_subtree(config, "service")

        # Assert
        self.assertEqual({"shared.database"}, result)

    def test_analyze_subtree__MultipleInterpolations__ReturnsAllPaths(self):
        # Arrange
        config = {
            "defaults": {"lr": 0.01, "layers": 50},
            "model": {
                "learning_rate": "${/defaults.lr}",
                "num_layers": "${/defaults.layers}",
            },
        }

        # Act
        result = self.analyzer.analyze_subtree(config, "model")

        # Assert
        self.assertEqual({"defaults.lr", "defaults.layers"}, result)

    def test_analyze_subtree__EmbeddedInterpolation__ReturnsPath(self):
        # Arrange
        config = {
            "defaults": {"name": "resnet"},
            "model": {
                "description": "Model name: ${/defaults.name}",
            },
        }

        # Act
        result = self.analyzer.analyze_subtree(config, "model")

        # Assert
        self.assertEqual({"defaults.name"}, result)

    def test_analyze_subtree__OnlyReturnsExternalPaths__InternalPathsExcluded(self):
        # Arrange
        config = {
            "model": {
                "base_lr": 0.01,
                "lr": "${./base_lr}",  # Internal reference
            },
        }

        # Act
        result = self.analyzer.analyze_subtree(config, "model")

        # Assert
        # ./base_lr from model.lr resolves to model.base_lr which is internal
        # So should not appear in dependencies
        self.assertNotIn("model.base_lr", result)

    def test_analyze_subtree__EmptyRootPath__AnalyzesEntireConfig(self):
        # Arrange
        config = {
            "model": {
                "lr": "${/training.lr}",
            },
            "training": {
                "lr": 0.01,
            },
        }

        # Act
        result = self.analyzer.analyze_subtree(config, "")

        # Assert
        # When analyzing entire config, training.lr is internal
        self.assertEqual(set(), result)

    def test_analyze_subtree__EnvInterpolation__IgnoredAsNotConfigPath(self):
        # Arrange
        config = {
            "model": {
                "api_key": "${env:API_KEY}",
            },
        }

        # Act
        result = self.analyzer.analyze_subtree(config, "model")

        # Assert
        self.assertEqual(set(), result)

    def test_analyze_subtree__AppResolverInterpolation__IgnoredAsNotConfigPath(self):
        # Arrange
        config = {
            "model": {
                "id": "${app:uuid}",
            },
        }

        # Act
        result = self.analyzer.analyze_subtree(config, "model")

        # Assert
        self.assertEqual(set(), result)

    def test_analyze_subtree__ListWithInterpolations__ExtractsFromList(self):
        # Arrange
        config = {
            "defaults": {"item1": "a", "item2": "b"},
            "model": {
                "items": ["${/defaults.item1}", "${/defaults.item2}"],
            },
        }

        # Act
        result = self.analyzer.analyze_subtree(config, "model")

        # Assert
        self.assertEqual({"defaults.item1", "defaults.item2"}, result)

    def test_analyze_subtree__InvalidPath__ReturnsEmptySet(self):
        # Arrange
        config = {"model": {"lr": 0.01}}

        # Act
        result = self.analyzer.analyze_subtree(config, "nonexistent")

        # Assert
        self.assertEqual(set(), result)


class DependencyAnalyzerExtractPathsTests(unittest.TestCase):
    """Tests for DependencyAnalyzer.extract_paths_from_expression method."""

    def setUp(self) -> None:
        self.analyzer = DependencyAnalyzer()

    def test_extract_paths_from_expression__AbsolutePath__ReturnsPath(self):
        # Arrange
        expression = "/model.lr"

        # Act
        result = self.analyzer.extract_paths_from_expression(expression)

        # Assert
        self.assertEqual({"model.lr"}, result)

    def test_extract_paths_from_expression__RelativePath__ReturnsAbsolutePath(self):
        # Arrange
        expression = "./local.value"

        # Act
        result = self.analyzer.extract_paths_from_expression(
            expression, current_path="config.model.lr"
        )

        # Assert
        # ./local.value from config.model.lr -> config.model.local.value
        self.assertIn("config.model.local.value", result)

    def test_extract_paths_from_expression__SimplePath__ReturnsPath(self):
        # Arrange
        expression = "model.lr"

        # Act
        result = self.analyzer.extract_paths_from_expression(expression)

        # Assert
        self.assertEqual({"model.lr"}, result)

    def test_extract_paths_from_expression__WithArithmetic__ExtractsAllPaths(self):
        # Arrange
        expression = "/model.lr * 2 + /defaults.scale"

        # Act
        result = self.analyzer.extract_paths_from_expression(expression)

        # Assert
        self.assertEqual({"model.lr", "defaults.scale"}, result)

    def test_extract_paths_from_expression__EnvVar__ReturnsEmpty(self):
        # Arrange
        expression = "env:API_KEY"

        # Act
        result = self.analyzer.extract_paths_from_expression(expression)

        # Assert
        self.assertEqual(set(), result)

    def test_extract_paths_from_expression__AppResolver__ReturnsEmpty(self):
        # Arrange
        expression = "app:uuid"

        # Act
        result = self.analyzer.extract_paths_from_expression(expression)

        # Assert
        self.assertEqual(set(), result)

    def test_extract_paths_from_expression__WithListIndex__ExtractsPath(self):
        # Arrange
        expression = "/items[0].name"

        # Act
        result = self.analyzer.extract_paths_from_expression(expression)

        # Assert
        self.assertIn("items[0].name", result)


class DependencyAnalyzerHasNestedInterpolationTests(unittest.TestCase):
    """Tests for DependencyAnalyzer.has_nested_interpolation method."""

    def setUp(self) -> None:
        self.analyzer = DependencyAnalyzer()

    def test_has_nested_interpolation__NoNesting__ReturnsFalse(self):
        # Arrange
        expression = "${/model.lr}"

        # Act
        result = self.analyzer.has_nested_interpolation(expression)

        # Assert
        self.assertFalse(result)

    def test_has_nested_interpolation__WithNesting__ReturnsTrue(self):
        # Arrange
        expression = "${/configs.${./source}.lr}"

        # Act
        result = self.analyzer.has_nested_interpolation(expression)

        # Assert
        self.assertTrue(result)


class DependencyAnalyzerFindUnresolvedRefsTests(unittest.TestCase):
    """Tests for DependencyAnalyzer.find_unresolved_refs method."""

    def setUp(self) -> None:
        self.analyzer = DependencyAnalyzer()

    def test_find_unresolved_refs__NoRefs__ReturnsEmptyDict(self):
        # Arrange
        config = {"model": {"lr": 0.01}}

        # Act
        result = self.analyzer.find_unresolved_refs(config, "model")

        # Assert
        self.assertEqual({}, result)

    def test_find_unresolved_refs__WithRef__ReturnsRefPath(self):
        # Arrange
        config = {
            "model": {
                "_ref_": "./model.yaml",
            }
        }

        # Act
        result = self.analyzer.find_unresolved_refs(config, "")

        # Assert
        self.assertEqual({"model": "./model.yaml"}, result)

    def test_find_unresolved_refs__NestedRef__FindsNested(self):
        # Arrange
        config = {
            "training": {
                "model": {
                    "_ref_": "./models/resnet.yaml",
                },
            },
        }

        # Act
        result = self.analyzer.find_unresolved_refs(config, "training")

        # Assert
        self.assertEqual({"training.model": "./models/resnet.yaml"}, result)

    def test_find_unresolved_refs__MultipleRefs__FindsAll(self):
        # Arrange
        config = {
            "model": {"_ref_": "./model.yaml"},
            "data": {"_ref_": "./data.yaml"},
        }

        # Act
        result = self.analyzer.find_unresolved_refs(config, "")

        # Assert
        self.assertEqual(
            {"model": "./model.yaml", "data": "./data.yaml"},
            result,
        )


class DependencyAnalyzerIsDescendantOfTests(unittest.TestCase):
    """Tests for DependencyAnalyzer._is_descendant_of method."""

    def setUp(self) -> None:
        self.analyzer = DependencyAnalyzer()

    def test_is_descendant_of__DirectChild__ReturnsTrue(self):
        # Arrange & Act
        result = self.analyzer._is_descendant_of("model.lr", "model")

        # Assert
        self.assertTrue(result)

    def test_is_descendant_of__NestedChild__ReturnsTrue(self):
        # Arrange & Act
        result = self.analyzer._is_descendant_of("model.layers.count", "model")

        # Assert
        self.assertTrue(result)

    def test_is_descendant_of__SamePath__ReturnsTrue(self):
        # Arrange & Act
        result = self.analyzer._is_descendant_of("model", "model")

        # Assert
        self.assertTrue(result)

    def test_is_descendant_of__NotDescendant__ReturnsFalse(self):
        # Arrange & Act
        result = self.analyzer._is_descendant_of("training.lr", "model")

        # Assert
        self.assertFalse(result)

    def test_is_descendant_of__EmptyAncestor__ReturnsTrue(self):
        # Arrange & Act
        result = self.analyzer._is_descendant_of("model.lr", "")

        # Assert
        self.assertTrue(result)

    def test_is_descendant_of__EmptyPath__ReturnsFalse(self):
        # Arrange & Act
        result = self.analyzer._is_descendant_of("", "model")

        # Assert
        self.assertFalse(result)

    def test_is_descendant_of__ListIndex__ReturnsTrue(self):
        # Arrange & Act
        result = self.analyzer._is_descendant_of("model.items[0]", "model")

        # Assert
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
