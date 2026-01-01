from unittest.case import TestCase

from rconfig.Provenance import InstanceRef, Provenance, ProvenanceEntry


class ProvenanceEntryTests(TestCase):
    """Tests for ProvenanceEntry dataclass."""

    def test_ProvenanceEntry__WithAllFields__StoresValues(self):
        # Act
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            overrode="base.yaml:3",
            instance=[InstanceRef("database", "app.yaml", 2)],
        )

        # Assert
        self.assertEqual(entry.file, "config.yaml")
        self.assertEqual(entry.line, 5)
        self.assertEqual(entry.overrode, "base.yaml:3")
        self.assertEqual(len(entry.instance), 1)
        self.assertEqual(entry.instance[0].path, "database")

    def test_ProvenanceEntry__WithDefaults__HasNoneForOptionalFields(self):
        # Act
        entry = ProvenanceEntry(file="config.yaml", line=1)

        # Assert
        self.assertEqual(entry.file, "config.yaml")
        self.assertEqual(entry.line, 1)
        self.assertIsNone(entry.overrode)
        self.assertIsNone(entry.instance)


class InstanceRefTests(TestCase):
    """Tests for InstanceRef dataclass."""

    def test_InstanceRef__CreatesCorrectly(self):
        # Act
        ref = InstanceRef(path="/shared.database", file="app.yaml", line=10)

        # Assert
        self.assertEqual(ref.path, "/shared.database")
        self.assertEqual(ref.file, "app.yaml")
        self.assertEqual(ref.line, 10)


class ProvenanceTests(TestCase):
    """Tests for Provenance class."""

    def test_add_and_get__SimpleValue__ReturnsEntry(self):
        # Arrange
        prov = Provenance()

        # Act
        prov.add("model.layers", file="config.yaml", line=5)
        entry = prov.get("model.layers")

        # Assert
        self.assertIsNotNone(entry)
        self.assertEqual(entry.file, "config.yaml")
        self.assertEqual(entry.line, 5)

    def test_get__NonExistentPath__ReturnsNone(self):
        # Arrange
        prov = Provenance()

        # Act
        entry = prov.get("nonexistent")

        # Assert
        self.assertIsNone(entry)

    def test_add__WithOverride__StoresOverrideInfo(self):
        # Arrange
        prov = Provenance()

        # Act
        prov.add("model.layers", file="trainer.yaml", line=5, overrode="model.yaml:2")
        entry = prov.get("model.layers")

        # Assert
        self.assertEqual(entry.overrode, "model.yaml:2")

    def test_add__WithInstanceChain__StoresInstanceRefs(self):
        # Arrange
        prov = Provenance()
        chain = [
            InstanceRef("alias", "app.yaml", 5),
            InstanceRef("database", "app.yaml", 2),
        ]

        # Act
        prov.add("service.db", file="app.yaml", line=9, instance=chain)
        entry = prov.get("service.db")

        # Assert
        self.assertEqual(len(entry.instance), 2)
        self.assertEqual(entry.instance[0].path, "alias")
        self.assertEqual(entry.instance[1].path, "database")

    def test_items__MultipleEntries__IteratesAll(self):
        # Arrange
        prov = Provenance()
        prov.add("a", file="a.yaml", line=1)
        prov.add("b", file="b.yaml", line=2)
        prov.add("c", file="c.yaml", line=3)

        # Act
        items = list(prov.items())

        # Assert
        self.assertEqual(len(items), 3)
        paths = [path for path, _ in items]
        self.assertIn("a", paths)
        self.assertIn("b", paths)
        self.assertIn("c", paths)

    def test_str__EmptyConfig__ReturnsEmptyString(self):
        # Arrange
        prov = Provenance()

        # Act
        result = str(prov)

        # Assert
        self.assertEqual(result, "")

    def test_str__SimpleConfig__FormatsWithAnnotations(self):
        # Arrange
        prov = Provenance()
        prov.add("_target_", file="trainer.yaml", line=1)
        prov.add("model", file="trainer.yaml", line=2)
        prov.add("model.layers", file="trainer.yaml", line=3)
        prov.set_config({
            "_target_": "Trainer",
            "model": {
                "layers": 50,
            },
        })

        # Act
        result = str(prov)

        # Assert
        self.assertIn("_target_: Trainer", result)
        self.assertIn("trainer.yaml:1", result)
        self.assertIn("trainer.yaml:3", result)
        self.assertIn("layers: 50", result)

    def test_str__WithOverride__ShowsOverrideAnnotation(self):
        # Arrange
        prov = Provenance()
        prov.add("model.layers", file="trainer.yaml", line=5, overrode="model.yaml:2")
        prov.set_config({
            "model": {
                "layers": 50,
            },
        })

        # Act
        result = str(prov)

        # Assert
        self.assertIn("overrode model.yaml:2", result)

    def test_str__WithList__FormatsListItems(self):
        # Arrange
        prov = Provenance()
        prov.add("callbacks[0]", file="config.yaml", line=5)
        prov.add("callbacks[1]", file="config.yaml", line=6)
        prov.set_config({
            "callbacks": ["logger", "checkpoint"],
        })

        # Act
        result = str(prov)

        # Assert
        self.assertIn("- logger", result)
        self.assertIn("- checkpoint", result)
        self.assertIn("config.yaml:5", result)

    def test_str__WithNullValue__FormatsAsNull(self):
        # Arrange
        prov = Provenance()
        prov.add("value", file="config.yaml", line=1)
        prov.set_config({"value": None})

        # Act
        result = str(prov)

        # Assert
        self.assertIn("value: null", result)

    def test_str__WithBoolValue__FormatsAsTrueFalse(self):
        # Arrange
        prov = Provenance()
        prov.add("enabled", file="config.yaml", line=1)
        prov.add("disabled", file="config.yaml", line=2)
        prov.set_config({"enabled": True, "disabled": False})

        # Act
        result = str(prov)

        # Assert
        self.assertIn("enabled: true", result)
        self.assertIn("disabled: false", result)

    def test_str__WithStringContainingSpecialChars__QuotesString(self):
        # Arrange
        prov = Provenance()
        prov.add("url", file="config.yaml", line=1)
        prov.set_config({"url": "http://localhost:8080"})

        # Act
        result = str(prov)

        # Assert
        # String contains ":" so should be quoted
        self.assertIn('"http://localhost:8080"', result)

    def test_str__NestedDicts__FormatsWithIndentation(self):
        # Arrange
        prov = Provenance()
        prov.add("level1", file="config.yaml", line=1)
        prov.add("level1.level2", file="config.yaml", line=2)
        prov.add("level1.level2.value", file="config.yaml", line=3)
        prov.set_config({
            "level1": {
                "level2": {
                    "value": 42,
                },
            },
        })

        # Act
        result = str(prov)
        lines = result.split("\n")

        # Assert
        self.assertIn("level1:", lines[0])
        self.assertIn("level2:", lines[1])
        self.assertIn("value: 42", lines[2])
        # Check indentation increases
        self.assertTrue(lines[1].startswith("  "))
        self.assertTrue(lines[2].startswith("    "))

    def test_str__NestedList__FormatsCorrectly(self):
        # Arrange
        prov = Provenance()
        prov.add("matrix[0]", file="config.yaml", line=1)
        prov.add("matrix[0][0]", file="config.yaml", line=2)
        prov.set_config({
            "matrix": [
                [1, 2, 3],
            ],
        })

        # Act
        result = str(prov)

        # Assert
        self.assertIn("-", result)  # List items use dashes

    def test_str__DictInList__FormatsCorrectly(self):
        # Arrange
        prov = Provenance()
        prov.add("items[0]", file="config.yaml", line=1)
        prov.add("items[0].name", file="config.yaml", line=2)
        prov.set_config({
            "items": [
                {"name": "first"},
            ],
        })

        # Act
        result = str(prov)

        # Assert
        self.assertIn("-", result)
        self.assertIn("name: first", result)

    def test_str__NoAnnotationForPath__OmitsAnnotation(self):
        # Arrange
        prov = Provenance()
        prov.add("a", file="config.yaml", line=1)
        # Note: "b" is NOT added to provenance
        prov.set_config({"a": 1, "b": 2})

        # Act
        result = str(prov)

        # Assert
        self.assertIn("a: 1", result)
        self.assertIn("config.yaml:1", result)
        self.assertIn("b: 2", result)
        # "b" line should not have annotation


class ProvenanceEdgeCaseTests(TestCase):
    """Edge case tests for Provenance."""

    def test_add__OverwritesExistingEntry(self):
        # Arrange
        prov = Provenance()
        prov.add("path", file="first.yaml", line=1)

        # Act
        prov.add("path", file="second.yaml", line=5)
        entry = prov.get("path")

        # Assert
        self.assertEqual(entry.file, "second.yaml")
        self.assertEqual(entry.line, 5)

    def test_items__EmptyProvenance__ReturnsEmptyIterator(self):
        # Arrange
        prov = Provenance()

        # Act
        items = list(prov.items())

        # Assert
        self.assertEqual(items, [])

    def test_str__StringWithQuotes__QuotesCorrectly(self):
        # Arrange
        prov = Provenance()
        prov.add("value", file="config.yaml", line=1)
        prov.set_config({"value": "'quoted'"})

        # Act
        result = str(prov)

        # Assert
        self.assertIn('"\'quoted\'"', result)


class ProvenanceCoverageTests(TestCase):
    """Tests to improve Provenance coverage for edge cases."""

    def test_format_value__RootScalar__FormatsWithAnnotation(self):
        """Test formatting a scalar value at the root level."""
        # Arrange - lines 166-168
        prov = Provenance()
        prov.add("", file="config.yaml", line=1)  # Root-level entry

        # Call the internal method directly
        lines: list[str] = []
        prov._format_value("scalar_value", "", lines, 0)

        # Assert - should format the scalar with annotation
        self.assertEqual(len(lines), 1)
        self.assertIn("scalar_value", lines[0])

    def test_format_value__RootScalarWithProvenance__IncludesAnnotation(self):
        """Test formatting a scalar value at the root with provenance entry."""
        # Arrange - lines 166-168
        prov = Provenance()
        prov.add("", file="config.yaml", line=42)

        # Call the internal method directly
        lines: list[str] = []
        prov._format_value(42, "", lines, 0)

        # Assert - should include the provenance annotation
        self.assertEqual(len(lines), 1)
        self.assertIn("42", lines[0])
        self.assertIn("config.yaml:42", lines[0])
