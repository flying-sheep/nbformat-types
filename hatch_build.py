"""Build hook to generate files."""

from __future__ import annotations

from importlib.resources import files
from itertools import count
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, cast

import jsonschema_gentypes.configuration as jgc
import nbformat
from hatchling.builders.config import BuilderConfig
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from jsonschema_gentypes.cli import process_config

if TYPE_CHECKING:
    from typing import Any


HERE = Path(__file__).parent


Ver = tuple[int, int] | tuple[None, None]
"""Version type. `(None, None)` is used for the latest version."""


def _get_schemas() -> dict[Ver, tuple[str, str]]:
    nb_files = files(nbformat)
    return {
        v: (file_name, (nb_files / f"v{mod.nbformat}" / file_name).read_text())
        for mod in cast("dict[str, nbformat.v4]", nbformat.versions).values()  # pyright: ignore[reportInvalidTypeForm]
        for v, file_name in cast("dict[Ver, str]", mod.nbformat_schema).items()  # pyright: ignore[reportUnknownMemberType]
    }


class CustomBuildHook(BuildHookInterface[BuilderConfig]):
    """Build hook to generate files."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Initialize the build hook."""
        del version, build_data
        min_python = next(
            v
            for minor in count(11)
            if (v := f"3.{minor}")
            in self.build_config.builder.metadata.core.python_constraint  # pyright: ignore[reportUnknownMemberType]
        )

        write_dir = Path(self.config["dir"])

        with TemporaryDirectory() as _tmp:
            tmp = Path(_tmp)
            schemas = {
                v: tmp / name
                for v, (name, schema) in _get_schemas().items()
                if (tmp / name).write_text(schema)
            }

            cfg = jgc.Configuration(
                pre_commit=jgc.PreCommitConfiguration(enable=True),
                python_version=min_python,
                generate=[
                    jgc.GenerateItem(
                        source=str(path),
                        destination=str(write_dir / f"{v[0]}_{v[1]}"),
                        root_name="Document",
                    )
                    for v, path in schemas.items()
                    if v != (None, None)
                ],
            )

            process_config(cfg, [])
