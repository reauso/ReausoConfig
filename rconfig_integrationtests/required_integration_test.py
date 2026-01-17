"""Integration tests for _required_ value functionality.

These tests verify that _required_ values are properly detected and validated
when using the high-level rc.instantiate() and rc.validate() APIs.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from unittest import TestCase

import rconfig as rc
from rconfig import RequiredValueError


# Test dataclasses
@dataclass
class DatabaseConfig:
    url: str
    timeout: int = 30


@dataclass
class AppConfig:
    api_key: str
    port: int = 8080
    database: DatabaseConfig | None = None


# Path to config files directory
CONFIG_DIR = Path(__file__).parent / "config_files"


class RequiredValueInstantiateTests(TestCase):
    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("app", AppConfig)
        rc.register("database", DatabaseConfig)

    def test_instantiate__RequiredNotProvided__RaisesRequiredValueError(self):
        config_path = CONFIG_DIR / "required_values.yaml"

        with self.assertRaises(RequiredValueError) as ctx:
            rc.instantiate(config_path, cli_overrides=False)

        error = ctx.exception
        self.assertEqual(len(error.missing), 3)
        paths = {path for path, _ in error.missing}
        self.assertIn("api_key", paths)
        self.assertIn("database.url", paths)
        self.assertIn("database.timeout", paths)

    def test_instantiate__AllRequiredProvidedProgrammatically__Succeeds(self):
        config_path = CONFIG_DIR / "required_values.yaml"

        app = rc.instantiate(
            config_path,
            overrides={
                "api_key": "secret123",
                "database.url": "postgresql://localhost:5432",
                "database.timeout": 60,
            },
            cli_overrides=False,
        )

        self.assertEqual(app.api_key, "secret123")
        self.assertEqual(app.port, 8080)
        self.assertEqual(app.database.url, "postgresql://localhost:5432")
        self.assertEqual(app.database.timeout, 60)

    def test_instantiate__PartialRequiredProvided__RaisesErrorForRemaining(self):
        config_path = CONFIG_DIR / "required_values.yaml"

        with self.assertRaises(RequiredValueError) as ctx:
            rc.instantiate(
                config_path,
                overrides={"api_key": "secret123"},
                cli_overrides=False,
            )

        error = ctx.exception
        self.assertEqual(len(error.missing), 2)
        paths = {path for path, _ in error.missing}
        self.assertIn("database.url", paths)
        self.assertIn("database.timeout", paths)
        self.assertNotIn("api_key", paths)

    def test_instantiate__RequiredSatisfiedByEnvInterpolation__Succeeds(self):
        config_path = CONFIG_DIR / "required_with_env.yaml"

        # Set env var
        os.environ["TEST_API_KEY"] = "env_secret_key"
        try:
            app = rc.instantiate(config_path, cli_overrides=False)

            self.assertEqual(app.api_key, "env_secret_key")
            self.assertEqual(app.port, 8080)
        finally:
            del os.environ["TEST_API_KEY"]

    def test_instantiate__TypedRequiredPreservesTypeInfo(self):
        config_path = CONFIG_DIR / "required_values.yaml"

        with self.assertRaises(RequiredValueError) as ctx:
            rc.instantiate(config_path, cli_overrides=False)

        error = ctx.exception
        # Find the typed marker
        types_by_path = {path: t for path, t in error.missing}
        self.assertEqual(types_by_path.get("database.timeout"), int)
        self.assertIsNone(types_by_path.get("api_key"))


class RequiredValueValidateTests(TestCase):
    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("app", AppConfig)
        rc.register("database", DatabaseConfig)

    def test_validate__RequiredNotProvided__ReturnsInvalidResult(self):
        config_path = CONFIG_DIR / "required_values.yaml"

        result = rc.validate(config_path, cli_overrides=False)

        self.assertFalse(result.valid)
        # Should have RequiredValueError in errors
        required_errors = [e for e in result.errors if isinstance(e, RequiredValueError)]
        self.assertEqual(len(required_errors), 1)
        self.assertEqual(len(required_errors[0].missing), 3)

    def test_validate__AllRequiredProvided__ReturnsValidResult(self):
        config_path = CONFIG_DIR / "required_values.yaml"

        result = rc.validate(
            config_path,
            overrides={
                "api_key": "secret123",
                "database.url": "postgresql://localhost:5432",
                "database.timeout": 60,
            },
            cli_overrides=False,
        )

        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)

    def test_validate__PartialRequiredProvided__ReturnsInvalidResult(self):
        config_path = CONFIG_DIR / "required_values.yaml"

        result = rc.validate(
            config_path,
            overrides={"api_key": "secret123"},
            cli_overrides=False,
        )

        self.assertFalse(result.valid)
        required_errors = [e for e in result.errors if isinstance(e, RequiredValueError)]
        self.assertEqual(len(required_errors), 1)
        self.assertEqual(len(required_errors[0].missing), 2)


class RequiredValueErrorMessageTests(TestCase):
    def setUp(self):
        rc._store._known_targets.clear()
        rc.register("app", AppConfig)
        rc.register("database", DatabaseConfig)

    def test_errorMessage__ContainsAllMissingPaths(self):
        config_path = CONFIG_DIR / "required_values.yaml"

        with self.assertRaises(RequiredValueError) as ctx:
            rc.instantiate(config_path, cli_overrides=False)

        error_str = str(ctx.exception)
        self.assertIn("api_key", error_str)
        self.assertIn("database.url", error_str)
        self.assertIn("database.timeout", error_str)

    def test_errorMessage__ContainsTypeHints(self):
        config_path = CONFIG_DIR / "required_values.yaml"

        with self.assertRaises(RequiredValueError) as ctx:
            rc.instantiate(config_path, cli_overrides=False)

        error_str = str(ctx.exception)
        self.assertIn("expected: int", error_str)
