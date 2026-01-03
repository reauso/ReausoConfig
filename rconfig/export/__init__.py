"""Config export/serialization module.

This module provides functionality for exporting resolved config data
to various formats (dict, YAML) without instantiation.

Example::

    import rconfig as rc
    from pathlib import Path

    # Export to dict
    config = rc.to_dict(Path("config.yaml"))

    # Export to YAML
    yaml_str = rc.to_yaml(Path("config.yaml"))

    # Using custom exporter
    exporter = MyCustomExporter()
    result = rc.export(Path("config.yaml"), exporter=exporter)
"""

from rconfig.export.base import Exporter
from rconfig.export.dict_exporter import DictExporter
from rconfig.export.yaml_exporter import YamlExporter
from rconfig.export.file_base import FileExporter
from rconfig.export.single_file_exporter import SingleFileExporter
from rconfig.export.multi_file_exporter import MultiFileExporter

__all__ = [
    "Exporter",
    "DictExporter",
    "YamlExporter",
    "FileExporter",
    "SingleFileExporter",
    "MultiFileExporter",
]
