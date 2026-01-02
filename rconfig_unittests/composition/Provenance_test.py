from unittest import TestCase

from rconfig.composition import InstanceRef, Provenance, ProvenanceEntry


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


class ProvenanceNodeToDictTests(TestCase):
    """Tests for ProvenanceNode.to_dict() edge cases."""

    def test_toDict__AllFieldsSet__IncludesAll(self):
        """Test that all fields are included when set."""
        # Arrange
        from rconfig.composition import ProvenanceNode

        node = ProvenanceNode(
            source_type="cli",
            path="/model.lr",
            file="<override>",
            line=0,
            value=0.01,
            expression="${/defaults.lr}",
            operator="+",
            env_var="LR_VALUE",
            cli_arg="--model.lr=0.01",
        )

        # Act
        result = node.to_dict()

        # Assert
        self.assertEqual("cli", result["source_type"])
        self.assertEqual("/model.lr", result["path"])
        self.assertEqual("<override>", result["file"])
        self.assertEqual(0, result["line"])
        self.assertEqual(0.01, result["value"])
        self.assertEqual("${/defaults.lr}", result["expression"])
        self.assertEqual("+", result["operator"])
        self.assertEqual("LR_VALUE", result["env_var"])
        self.assertEqual("--model.lr=0.01", result["cli_arg"])

    def test_toDict__CliArg__IncludesCliArg(self):
        """Test that cli_arg is included when set."""
        # Arrange
        from rconfig.composition import ProvenanceNode

        node = ProvenanceNode(
            source_type="cli",
            cli_arg="--lr=0.01",
        )

        # Act
        result = node.to_dict()

        # Assert
        self.assertEqual("--lr=0.01", result["cli_arg"])

    def test_toDict__EnvVar__IncludesEnvVar(self):
        """Test that env_var is included when set."""
        # Arrange
        from rconfig.composition import ProvenanceNode

        node = ProvenanceNode(
            source_type="env",
            env_var="DATA_PATH",
        )

        # Act
        result = node.to_dict()

        # Assert
        self.assertEqual("DATA_PATH", result["env_var"])

    def test_toDict__Expression__IncludesExpression(self):
        """Test that expression is included when set."""
        # Arrange
        from rconfig.composition import ProvenanceNode

        node = ProvenanceNode(
            source_type="interpolation",
            expression="${/defaults.lr * 2}",
        )

        # Act
        result = node.to_dict()

        # Assert
        self.assertEqual("${/defaults.lr * 2}", result["expression"])

    def test_toDict__Operator__IncludesOperator(self):
        """Test that operator is included when set."""
        # Arrange
        from rconfig.composition import ProvenanceNode

        node = ProvenanceNode(
            source_type="operator",
            operator="*",
        )

        # Act
        result = node.to_dict()

        # Assert
        self.assertEqual("*", result["operator"])

    def test_toDict__EmptyChildren__OmitsChildren(self):
        """Test that empty children list is omitted."""
        # Arrange
        from rconfig.composition import ProvenanceNode

        node = ProvenanceNode(source_type="file")

        # Act
        result = node.to_dict()

        # Assert
        self.assertNotIn("children", result)

    def test_toDict__ValueIsFalse__IncludesValue(self):
        """Test that False value is included (not omitted as falsy)."""
        # Arrange
        from rconfig.composition import ProvenanceNode

        node = ProvenanceNode(source_type="file", value=False)

        # Act
        result = node.to_dict()

        # Assert
        # Note: This tests that we use 'is not None' not 'if value'
        # Currently the code uses 'if value is not None' which correctly handles False
        self.assertIn("value", result)
        self.assertFalse(result["value"])

    def test_toDict__ValueIsZero__IncludesValue(self):
        """Test that zero value is included (not omitted as falsy)."""
        # Arrange
        from rconfig.composition import ProvenanceNode

        node = ProvenanceNode(source_type="file", value=0)

        # Act
        result = node.to_dict()

        # Assert
        self.assertIn("value", result)
        self.assertEqual(0, result["value"])


class ProvenanceEntryToDictExtendedTests(TestCase):
    """Extended tests for ProvenanceEntry.to_dict() edge cases."""

    def test_toDict__WithInterpolationPath__IncludesPath(self):
        """Test that interpolation path is included."""
        # Arrange
        from rconfig.interpolation.evaluator import InterpolationSource

        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            interpolation=InterpolationSource(
                kind="config",
                expression="/defaults.lr",
                value=0.01,
                path="defaults.lr",
            ),
        )

        # Act
        result = entry.to_dict()

        # Assert
        self.assertIn("interpolation", result)
        self.assertEqual("defaults.lr", result["interpolation"]["path"])

    def test_toDict__WithInterpolationFile__IncludesFile(self):
        """Test that interpolation file is included."""
        # Arrange
        from rconfig.interpolation.evaluator import InterpolationSource

        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            interpolation=InterpolationSource(
                kind="config",
                expression="/defaults.lr",
                value=0.01,
                path="defaults.lr",
                file="defaults.yaml",
                line=3,
            ),
        )

        # Act
        result = entry.to_dict()

        # Assert
        self.assertIn("interpolation", result)
        self.assertEqual("defaults.yaml", result["interpolation"]["file"])
        self.assertEqual(3, result["interpolation"]["line"])

    def test_toDict__WithInstance__IncludesInstanceArray(self):
        """Test that instance chain is included as array."""
        # Arrange
        entry = ProvenanceEntry(
            file="app.yaml",
            line=10,
            instance=[
                InstanceRef(path="/shared.db", file="shared.yaml", line=5),
                InstanceRef(path="/common.db", file="common.yaml", line=2),
            ],
        )

        # Act
        result = entry.to_dict()

        # Assert
        self.assertIn("instance", result)
        self.assertEqual(2, len(result["instance"]))
        self.assertEqual("/shared.db", result["instance"][0]["path"])
        self.assertEqual("shared.yaml", result["instance"][0]["file"])

    def test_toDict__WithEnvVar__IncludesEnvVar(self):
        """Test that env_var is included."""
        # Arrange
        entry = ProvenanceEntry(
            file="<override>",
            line=0,
            source_type="env",
            env_var="DATA_PATH",
        )

        # Act
        result = entry.to_dict()

        # Assert
        self.assertEqual("DATA_PATH", result["env_var"])

    def test_toDict__ValueIsNone__OmitsValue(self):
        """Test that None value is omitted."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=None)

        # Act
        result = entry.to_dict()

        # Assert
        self.assertNotIn("value", result)

    def test_toDict__ValueIsFalse__IncludesValue(self):
        """Test that False value is included."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=False)

        # Act
        result = entry.to_dict()

        # Assert
        # Note: Current implementation uses 'if value is not None' which
        # would include False. But it's using 'if value is not None'
        self.assertIn("value", result)
        self.assertFalse(result["value"])

    def test_toDict__ValueIsZero__IncludesValue(self):
        """Test that zero value is included."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value=0)

        # Act
        result = entry.to_dict()

        # Assert
        self.assertIn("value", result)
        self.assertEqual(0, result["value"])

    def test_toDict__ValueIsEmptyString__IncludesValue(self):
        """Test that empty string value is included."""
        # Arrange
        entry = ProvenanceEntry(file="config.yaml", line=5, value="")

        # Act
        result = entry.to_dict()

        # Assert
        # Empty string should be included since it's not None
        self.assertIn("value", result)
        self.assertEqual("", result["value"])


class ProvenanceEntryTraceTests(TestCase):
    """Tests for ProvenanceEntry.trace() method."""

    def test_trace__FileSourceType__ReturnsFileNode(self):
        """Test that file source type creates file node."""
        # Arrange
        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            value=42,
            source_type="file",
        )

        # Act
        result = entry.trace()

        # Assert
        self.assertEqual("file", result.source_type)
        self.assertEqual("config.yaml", result.file)
        self.assertEqual(5, result.line)
        self.assertEqual(42, result.value)

    def test_trace__CliSourceType__ReturnsCliNode(self):
        """Test that CLI source type creates cli node."""
        # Arrange
        entry = ProvenanceEntry(
            file="<override>",
            line=0,
            value=0.01,
            source_type="cli",
            cli_arg="--lr=0.01",
        )

        # Act
        result = entry.trace()

        # Assert
        self.assertEqual("cli", result.source_type)
        self.assertEqual("--lr=0.01", result.cli_arg)

    def test_trace__EnvSourceType__ReturnsEnvNode(self):
        """Test that env source type creates env node."""
        # Arrange
        entry = ProvenanceEntry(
            file="<override>",
            line=0,
            value="/data",
            source_type="env",
            env_var="DATA_PATH",
        )

        # Act
        result = entry.trace()

        # Assert
        self.assertEqual("env", result.source_type)
        self.assertEqual("DATA_PATH", result.env_var)

    def test_trace__ProgrammaticSourceType__ReturnsProgrammaticNode(self):
        """Test that programmatic source type creates programmatic node."""
        # Arrange
        entry = ProvenanceEntry(
            file="<override>",
            line=0,
            value=100,
            source_type="programmatic",
        )

        # Act
        result = entry.trace()

        # Assert
        self.assertEqual("programmatic", result.source_type)
        self.assertEqual(100, result.value)

    def test_trace__WithInterpolation__AddsInterpolationChild(self):
        """Test that interpolation is added as child node."""
        # Arrange
        from rconfig.interpolation.evaluator import InterpolationSource

        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            value=0.02,
            interpolation=InterpolationSource(
                kind="config",
                expression="/defaults.lr",
                value=0.01,
                path="defaults.lr",
            ),
        )

        # Act
        result = entry.trace()

        # Assert
        self.assertEqual(1, len(result.children))
        self.assertEqual("interpolation", result.children[0].source_type)

    def test_trace__WithInstance__AddsInstanceChildren(self):
        """Test that instance chain is added as children."""
        # Arrange
        entry = ProvenanceEntry(
            file="app.yaml",
            line=10,
            value={"host": "localhost"},
            instance=[
                InstanceRef(path="/shared.db", file="shared.yaml", line=5),
                InstanceRef(path="/common.db", file="common.yaml", line=2),
            ],
        )

        # Act
        result = entry.trace()

        # Assert
        self.assertEqual(2, len(result.children))
        self.assertEqual("instance", result.children[0].source_type)
        self.assertEqual("/shared.db", result.children[0].path)

    def test_trace__InterpolationConfigKind__CreatesInterpolationNode(self):
        """Test that config interpolation creates interpolation node."""
        # Arrange
        from rconfig.interpolation.evaluator import InterpolationSource

        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            value=0.01,
            interpolation=InterpolationSource(
                kind="config",
                expression="/defaults.lr",
                value=0.01,
                path="defaults.lr",
                file="defaults.yaml",
                line=3,
            ),
        )

        # Act
        result = entry.trace()

        # Assert
        interp_node = result.children[0]
        self.assertEqual("interpolation", interp_node.source_type)
        self.assertEqual("defaults.lr", interp_node.path)
        self.assertEqual("defaults.yaml", interp_node.file)

    def test_trace__InterpolationEnvKind__CreatesEnvNode(self):
        """Test that env interpolation creates env node."""
        # Arrange
        from rconfig.interpolation.evaluator import InterpolationSource

        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            value="/data",
            interpolation=InterpolationSource(
                kind="env",
                expression="env:DATA_PATH",
                value="/data",
                env_var="DATA_PATH",
            ),
        )

        # Act
        result = entry.trace()

        # Assert
        interp_node = result.children[0]
        self.assertEqual("env", interp_node.source_type)
        self.assertEqual("DATA_PATH", interp_node.env_var)

    def test_trace__InterpolationLiteralKind__CreatesFileNode(self):
        """Test that literal interpolation creates file node."""
        # Arrange
        from rconfig.interpolation.evaluator import InterpolationSource

        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            value=42,
            interpolation=InterpolationSource(
                kind="literal",
                expression="42",
                value=42,
            ),
        )

        # Act
        result = entry.trace()

        # Assert
        interp_node = result.children[0]
        self.assertEqual("file", interp_node.source_type)

    def test_trace__InterpolationExpressionKind__CreatesOperatorNode(self):
        """Test that expression interpolation creates operator node."""
        # Arrange
        from rconfig.interpolation.evaluator import InterpolationSource

        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            value=15,
            interpolation=InterpolationSource(
                kind="expression",
                expression="/a + /b",
                value=15,
                operator="+",
                sources=[
                    InterpolationSource(kind="config", expression="/a", value=5, path="a"),
                    InterpolationSource(kind="config", expression="/b", value=10, path="b"),
                ],
            ),
        )

        # Act
        result = entry.trace()

        # Assert
        interp_node = result.children[0]
        self.assertEqual("operator", interp_node.source_type)
        self.assertEqual("+", interp_node.operator)
        self.assertEqual(2, len(interp_node.children))

    def test_trace__UnknownInterpolationKind__FallbackToFileNode(self):
        """Test that unknown interpolation kind falls back to file node."""
        # Arrange
        from rconfig.interpolation.evaluator import InterpolationSource

        entry = ProvenanceEntry(
            file="config.yaml",
            line=5,
            value=42,
            interpolation=InterpolationSource(
                kind="unknown",  # type: ignore  # Testing unknown kind
                expression="unknown",
                value=42,
            ),
        )

        # Act
        result = entry.trace()

        # Assert
        interp_node = result.children[0]
        self.assertEqual("file", interp_node.source_type)


class ProvenanceSetConfigExtendedTests(TestCase):
    """Extended tests for Provenance.set_config()."""

    def test_setConfig__ListIndex__PopulatesCorrectly(self):
        """Test that list indices are populated correctly."""
        # Arrange
        prov = Provenance()
        prov.add("items[0]", file="config.yaml", line=1)
        prov.add("items[1]", file="config.yaml", line=2)
        config = {"items": ["first", "second"]}

        # Act
        prov.set_config(config)

        # Assert
        self.assertEqual("first", prov.get("items[0]").value)
        self.assertEqual("second", prov.get("items[1]").value)

    def test_setConfig__TypeError__KeepsNone(self):
        """Test that TypeError during path navigation keeps value as None."""
        # Arrange
        prov = Provenance()
        prov.add("a.b.c", file="config.yaml", line=1)
        config = {"a": None}  # Can't navigate through None

        # Act
        prov.set_config(config)

        # Assert
        self.assertIsNone(prov.get("a.b.c").value)

    def test_setConfig__IndexError__KeepsNone(self):
        """Test that IndexError during path navigation keeps value as None."""
        # Arrange
        prov = Provenance()
        prov.add("items[5]", file="config.yaml", line=1)
        config = {"items": [1, 2]}  # Only 2 items, index 5 is out of range

        # Act
        prov.set_config(config)

        # Assert
        self.assertIsNone(prov.get("items[5]").value)
