"""Config export/serialization module.

This module provides functionality for exporting resolved config data
to various formats (dict, YAML, JSON, TOML) without instantiation.

Example::

    import rconfig as rc
    from pathlib import Path

    # Export to dict
    config = rc.to_dict(Path("config.yaml"))

    # Export to YAML
    yaml_str = rc.to_yaml(Path("config.yaml"))

    # Export to JSON
    json_str = rc.to_json(Path("config.yaml"))

    # Export to TOML
    toml_str = rc.to_toml(Path("config.yaml"))

    # Using custom exporter
    exporter = MyCustomExporter()
    result = rc.export(Path("config.yaml"), exporter=exporter)

    # File export with auto-detected format
    rc.to_file(Path("config.yaml"), Path("output.json"))
"""

from rconfig.export.base import Exporter
from rconfig.export.dict_exporter import DictExporter
from rconfig.export.yaml_exporter import YamlExporter
from rconfig.export.json_exporter import JsonExporter
from rconfig.export.toml_exporter import TomlExporter
from rconfig.export.file_base import FileExporter
from rconfig.export.single_file_exporter import SingleFileExporter
from rconfig.export.multi_file_exporter import MultiFileExporter
from rconfig.export.registry import (
    register_exporter,
    unregister_exporter,
    get_exporter,
    supported_exporter_extensions,
)

__all__ = [
    "Exporter",
    "DictExporter",
    "YamlExporter",
    "JsonExporter",
    "TomlExporter",
    "FileExporter",
    "SingleFileExporter",
    "MultiFileExporter",
    "register_exporter",
    "unregister_exporter",
    "get_exporter",
    "supported_exporter_extensions",
]
