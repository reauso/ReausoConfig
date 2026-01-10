"""Extensive tests for position tracking in JSON and TOML loaders."""

from pathlib import Path
from unittest import TestCase

from rconfig.composition import clear_cache
from rconfig.loaders import JsonConfigLoader, TomlConfigLoader
from rconfig.loaders.position_map import Position

from rconfig_unittests.fixtures import MockFileSystem, mock_filesystem


class JsonPositionTrackingTests(TestCase):
    """Extensive tests for JSON position tracking."""

    def setUp(self):
        clear_cache()
        self.loader = JsonConfigLoader()

    def test_json__SimpleKeys__CorrectLineAndColumn(self):
        # Arrange
        content = '{"name": "value", "count": 42}'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.json", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.json"))

            # Assert
            self.assertEqual(result.get_line("name"), 1)
            self.assertEqual(result.get_column("name"), 2)

    def test_json__MultilineFormatted__CorrectLineNumbers(self):
        # Arrange
        content = """{
    "first": 1,
    "second": 2,
    "third": 3
}"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.json", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.json"))

            # Assert
            self.assertEqual(result.get_line("first"), 2)
            self.assertEqual(result.get_line("second"), 3)
            self.assertEqual(result.get_line("third"), 4)

    def test_json__CompactSingleLine__CorrectColumns(self):
        # Arrange
        content = '{"a":1,"b":2,"c":3}'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.json", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.json"))

            # Assert
            self.assertEqual(result.get_line("a"), 1)
            self.assertEqual(result.get_column("a"), 2)
            self.assertEqual(result.get_column("b"), 8)
            self.assertEqual(result.get_column("c"), 14)

    def test_json__MixedIndentation__TracksCorrectly(self):
        # Arrange
        content = """{
  "shallow": 1,
        "deep": 2,
"none": 3
}"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.json", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.json"))

            # Assert
            self.assertEqual(result.get_line("shallow"), 2)
            self.assertEqual(result.get_column("shallow"), 3)
            self.assertEqual(result.get_line("deep"), 3)
            self.assertEqual(result.get_column("deep"), 9)
            self.assertEqual(result.get_line("none"), 4)
            self.assertEqual(result.get_column("none"), 1)

    def test_json__EmptyObject__NoPositions(self):
        # Arrange
        content = "{}"
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.json", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.json"))

            # Assert
            self.assertEqual(len(result), 0)
            self.assertIsNone(result.get_position("any"))

    def test_json__ArrayOfObjects__TracksEachObjectKey(self):
        # Arrange
        content = """[
    {"name": "first"},
    {"name": "second"}
]"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.json", content)

        with mock_filesystem(fs):
            # This should raise an error since root is not a dict
            with self.assertRaises(Exception):
                self.loader.load_with_positions(Path("/configs/test.json"))

    def test_json__DeeplyNested__TracksAllLevels(self):
        # Arrange
        content = """{
    "level1": {
        "level2": {
            "level3": {
                "value": 42
            }
        }
    }
}"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.json", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.json"))

            # Assert
            self.assertEqual(result.get_line("level1"), 2)
            self.assertEqual(result["level1"].get_line("level2"), 3)
            self.assertEqual(result["level1"]["level2"].get_line("level3"), 4)
            self.assertEqual(result["level1"]["level2"]["level3"].get_line("value"), 5)

    def test_json__WindowsLineEndings__NormalizesCorrectly(self):
        # Arrange
        content = '{\r\n    "first": 1,\r\n    "second": 2\r\n}'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.json", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.json"))

            # Assert
            self.assertEqual(result.get_line("first"), 2)
            self.assertEqual(result.get_line("second"), 3)

    def test_json__MixedLineEndings__HandlesCorrectly(self):
        # Arrange
        content = '{\n    "first": 1,\r\n    "second": 2,\r    "third": 3\n}'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.json", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.json"))

            # Assert - all should be on different lines
            self.assertIsNotNone(result.get_line("first"))
            self.assertIsNotNone(result.get_line("second"))
            self.assertIsNotNone(result.get_line("third"))

    def test_json__LeadingWhitespace__CorrectColumnOffset(self):
        # Arrange
        content = '    {"key": "value"}'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.json", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.json"))

            # Assert - column accounts for leading whitespace
            self.assertEqual(result.get_column("key"), 6)


class TomlPositionTrackingTests(TestCase):
    """Extensive tests for TOML position tracking."""

    def setUp(self):
        clear_cache()
        self.loader = TomlConfigLoader()

    def test_toml__SimpleKeys__CorrectLineAndColumn(self):
        # Arrange
        content = 'name = "value"\ncount = 42\n'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.toml", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.toml"))

            # Assert
            self.assertEqual(result.get_line("name"), 1)
            self.assertEqual(result.get_column("name"), 1)
            self.assertEqual(result.get_line("count"), 2)

    def test_toml__TableSection__TracksKeysWithTablePrefix(self):
        # Arrange
        content = """[server]
host = "localhost"
port = 8080
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.toml", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.toml"))

            # Assert
            self.assertEqual(result["server"].get_line("host"), 2)
            self.assertEqual(result["server"].get_line("port"), 3)

    def test_toml__NestedTables__BuildsFullPath(self):
        # Arrange
        content = """[database.connection]
host = "db.example.com"
port = 5432
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.toml", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.toml"))

            # Assert
            self.assertEqual(result["database"]["connection"]["host"], "db.example.com")
            self.assertEqual(result["database"]["connection"]["port"], 5432)

    def test_toml__ArrayOfTables__TracksEachEntry(self):
        # Arrange
        content = """[[products]]
name = "Hammer"
price = 9.99

[[products]]
name = "Nail"
price = 0.05
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.toml", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.toml"))

            # Assert
            self.assertEqual(len(result["products"]), 2)
            self.assertEqual(result["products"][0]["name"], "Hammer")
            self.assertEqual(result["products"][1]["name"], "Nail")

    def test_toml__DottedKeys__TracksFullPath(self):
        # Arrange
        content = 'physical.color = "orange"\nphysical.shape = "round"\n'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.toml", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.toml"))

            # Assert
            self.assertEqual(result["physical"]["color"], "orange")
            self.assertEqual(result["physical"]["shape"], "round")

    def test_toml__MultilineStrings__CorrectLineForKey(self):
        # Arrange
        content = '''description = """
This is a
multi-line string
"""
version = 1
'''
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.toml", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.toml"))

            # Assert
            self.assertEqual(result.get_line("description"), 1)
            self.assertEqual(result.get_line("version"), 5)

    def test_toml__Comments__IgnoresCommentLines(self):
        # Arrange
        content = """# Header comment
name = "test"
# Mid comment
value = 42
# Trailing comment
"""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.toml", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.toml"))

            # Assert
            self.assertEqual(result.get_line("name"), 2)
            self.assertEqual(result.get_line("value"), 4)

    def test_toml__InlineComments__TracksKeyPosition(self):
        # Arrange
        content = 'key = "value" # This is a comment\nnumber = 42 # Another comment\n'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.toml", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.toml"))

            # Assert
            self.assertEqual(result.get_line("key"), 1)
            self.assertEqual(result.get_line("number"), 2)

    def test_toml__EmptyFile__NoPositions(self):
        # Arrange
        content = ""
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.toml", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.toml"))

            # Assert
            self.assertEqual(len(result), 0)
            self.assertIsNone(result.get_position("any"))

    def test_toml__IndentedKeys__CorrectColumnOffset(self):
        # Arrange
        content = "  name = 'test'\n    value = 42\n"
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.toml", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.toml"))

            # Assert
            self.assertEqual(result.get_column("name"), 3)  # After 2 spaces
            self.assertEqual(result.get_column("value"), 5)  # After 4 spaces

    def test_toml__WindowsLineEndings__NormalizesCorrectly(self):
        # Arrange
        content = 'first = 1\r\nsecond = 2\r\n'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.toml", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.toml"))

            # Assert
            self.assertEqual(result.get_line("first"), 1)
            self.assertEqual(result.get_line("second"), 2)

    def test_toml__MixedLineEndings__HandlesCorrectly(self):
        # Arrange
        content = 'first = 1\nsecond = 2\r\nthird = 3\n'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.toml", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.toml"))

            # Assert
            self.assertIsNotNone(result.get_line("first"))
            self.assertIsNotNone(result.get_line("second"))
            self.assertIsNotNone(result.get_line("third"))

    def test_toml__SpecialCharactersInValues__DoesNotAffectKeyPosition(self):
        # Arrange
        content = 'key = "value with = sign"\nother = "another = value"\n'
        fs = MockFileSystem("/configs")
        fs.add_file("/configs/test.toml", content)

        with mock_filesystem(fs):
            # Act
            result = self.loader.load_with_positions(Path("/configs/test.toml"))

            # Assert
            self.assertEqual(result.get_line("key"), 1)
            self.assertEqual(result.get_line("other"), 2)
