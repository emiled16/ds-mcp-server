from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML


class Yaml:
    """Namespace for YAML utilities."""

    @staticmethod
    def load_str(yaml_str: str) -> object:
        return Yaml.config().load(yaml_str)

    @staticmethod
    def load_file(file_path: Path) -> object:
        return Yaml.config().load(file_path)

    @staticmethod
    def dump_str(obj: object) -> str:
        """Dump the given object to a YAML string.

        Ref: https://stackoverflow.com/a/63179923/4406961.
        """
        with StringIO() as stream:
            Yaml.config().dump(obj, stream)
            return stream.getvalue()

    @staticmethod
    def dump_file(obj: object, destination_file: Path) -> None:
        """Dump the given object to the destination file."""
        Yaml.config().dump(obj, destination_file)

    @staticmethod
    def config() -> YAML:
        """YAML configuration with good indentation.

        Ref: https://stackoverflow.com/questions/25108581/python-yaml-dump-bad-indentation
        """
        yaml = YAML()
        yaml.sequence_dash_offset = 2
        yaml.sequence_indent = 4
        return yaml
