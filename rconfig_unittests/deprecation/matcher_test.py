"""Unit tests for PathMatcher."""

from unittest import TestCase

from rconfig.deprecation.matcher import PathMatcher, find_match, matches


class PathMatcherTests(TestCase):
    """Tests for the PathMatcher class."""

    def setUp(self) -> None:
        self.matcher = PathMatcher()

    # === Exact Match Tests ===

    def test_matches__ExactPath__MatchesOnlyExact(self):
        # Arrange
        pattern = "model.lr"
        path = "model.lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertTrue(result)

    def test_matches__ExactPath__NoMatchDifferentPath(self):
        # Arrange
        pattern = "model.lr"
        path = "other.lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertFalse(result)

    def test_matches__ExactPath__NoMatchSubstring(self):
        # Arrange
        pattern = "model"
        path = "model.lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertFalse(result)

    def test_matches__ExactPath__NoMatchSuperstring(self):
        # Arrange
        pattern = "model.lr"
        path = "model"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertFalse(result)

    # === Single Wildcard Tests ===

    def test_matches__SingleWildcard__MatchesOneLevel(self):
        # Arrange
        pattern = "*.lr"
        path = "model.lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertTrue(result)

    def test_matches__SingleWildcard__NoMatchMultipleLevels(self):
        # Arrange
        pattern = "*.lr"
        path = "a.b.lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertFalse(result)

    def test_matches__SingleWildcard__NoMatchEmpty(self):
        # Arrange
        pattern = "*.lr"
        path = ".lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertFalse(result)

    def test_matches__SingleWildcardAtEnd__MatchesSingleSegment(self):
        # Arrange
        pattern = "model.*"
        path = "model.lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertTrue(result)

    def test_matches__SingleWildcardInMiddle__MatchesPattern(self):
        # Arrange
        pattern = "model.*.lr"
        path = "model.encoder.lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertTrue(result)

    def test_matches__MultipleSingleWildcards__MatchesCorrectly(self):
        # Arrange
        pattern = "*.*.lr"
        path = "model.encoder.lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertTrue(result)

    # === Double Wildcard Tests ===

    def test_matches__DoubleWildcard__MatchesAnyDepth(self):
        # Arrange
        pattern = "**.lr"
        path = "a.b.c.lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertTrue(result)

    def test_matches__DoubleWildcard__MatchesSingleLevel(self):
        # Arrange
        pattern = "**.lr"
        path = "model.lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertTrue(result)

    def test_matches__DoubleWildcard__MatchesZeroLevels(self):
        # Arrange
        pattern = "**.lr"
        path = "lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertTrue(result)

    def test_matches__DoubleWildcardAtStart__MatchesSuffix(self):
        # Arrange
        pattern = "**.dropout"
        path = "model.encoder.dropout"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertTrue(result)

    def test_matches__DoubleWildcardInMiddle__MatchesAnyDepth(self):
        # Arrange
        pattern = "model.**.lr"
        path = "model.encoder.decoder.lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertTrue(result)

    def test_matches__DoubleWildcardInMiddle__MatchesZeroSegments(self):
        # Arrange
        pattern = "model.**.lr"
        path = "model.lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertTrue(result)

    def test_matches__DoubleWildcardAtEnd__MatchesAnySuffix(self):
        # Arrange
        pattern = "model.**"
        path = "model.encoder.lr"

        # Act
        result = self.matcher.matches(pattern, path)

        # Assert
        self.assertTrue(result)

    # === find_match Tests ===

    def test_findMatch__MultiplePatterns__ReturnsFirstMatch(self):
        # Arrange
        patterns = ["model.lr", "*.dropout", "**.hidden_size"]

        # Act
        result = self.matcher.find_match("encoder.dropout", patterns)

        # Assert
        self.assertEqual(result, "*.dropout")

    def test_findMatch__NoMatch__ReturnsNone(self):
        # Arrange
        patterns = ["model.lr", "encoder.lr"]

        # Act
        result = self.matcher.find_match("decoder.lr", patterns)

        # Assert
        self.assertIsNone(result)

    def test_findMatch__ExactMatchFirst__ReturnsExact(self):
        # Arrange
        patterns = ["model.lr", "*.lr", "**.lr"]

        # Act
        result = self.matcher.find_match("model.lr", patterns)

        # Assert
        self.assertEqual(result, "model.lr")

    def test_findMatch__EmptyPatterns__ReturnsNone(self):
        # Arrange
        patterns: list[str] = []

        # Act
        result = self.matcher.find_match("model.lr", patterns)

        # Assert
        self.assertIsNone(result)


class ModuleFunctionsTests(TestCase):
    """Tests for module-level convenience functions."""

    def test_matches__ModuleFunction__DelegatesToMatcher(self):
        # Act & Assert
        self.assertTrue(matches("model.lr", "model.lr"))
        self.assertFalse(matches("model.lr", "other.lr"))

    def test_findMatch__ModuleFunction__DelegatesToMatcher(self):
        # Arrange
        patterns = ["*.lr", "**.dropout"]

        # Act
        result = find_match("encoder.lr", patterns)

        # Assert
        self.assertEqual(result, "*.lr")
