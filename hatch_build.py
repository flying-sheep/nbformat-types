"""Build hook to generate files."""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from importlib.resources import files
from itertools import count
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, cast

import nbformat
from hatchling.builders.config import BuilderConfig
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from jsonschema_gentypes import configuration as jgc
from jsonschema_gentypes.cli import process_config

if TYPE_CHECKING:
    from typing import Any


HERE = Path(__file__).parent


INIT_TEMPLATE = '''\
"""``nbformat`` types for individual versions."""
from __future__ import annotations

from . import {imports}

__all__ = {all!r}
'''


def _get_schemas() -> dict[str, tuple[str, str]]:
    nb_files = files(nbformat)
    return {
        f"v{maj}_{min_}": (
            file_name,
            (nb_files / f"v{v}" / file_name).read_text(),
        )
        for v, mod in cast("dict[int, nbformat.v4]", nbformat.versions).items()  # pyright: ignore[reportInvalidTypeForm]
        for (maj, min_), file_name in cast(
            "dict[tuple[str, str] | tuple[None, None], str]",
            getattr(mod, "nbformat_schema", {}),
        ).items()
        if (maj, min_) != (None, None)
    }


class CustomBuildHook(BuildHookInterface[BuilderConfig]):
    """Build hook to generate files."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Initialize the build hook."""
        del version
        min_python = next(
            v
            for minor in count(11)
            if (v := f"3.{minor}")
            in self.build_config.builder.metadata.core.python_constraint  # pyright: ignore[reportUnknownMemberType]
        )

        # get write directory and set it as artifact (VCS-ignored dir to include)
        write_dir = Path(self.config["dir"])
        write_dir.mkdir(parents=True, exist_ok=True)

        build_data["artifacts"] = [str(write_dir)]

        # generate __init__.py
        schemas = _get_schemas()
        aliases = dict(
            current=f"v{nbformat.current_nbformat}_{nbformat.current_nbformat_minor}",
            **{
                f"v{v}": f"v{v}_{mod.nbformat_minor}"
                for v, mod in cast("dict[int, nbformat.v4]", nbformat.versions).items()  # pyright: ignore[reportInvalidTypeForm]
                if f"v{v}_0" in schemas
            },
        )

        (write_dir / "__init__.py").write_text(
            INIT_TEMPLATE.format(
                imports=", ".join(
                    (*schemas, *(f"{mod} as {name}" for name, mod in aliases.items()))
                ),
                all=[*aliases, *schemas],
            )
        )

        # generate individual versions
        with TemporaryDirectory() as _tmp:
            tmp = Path(_tmp)

            for name, schema in schemas.values():
                (tmp / name).write_text(schema)

            cfg = jgc.Configuration(
                pre_commit=jgc.PreCommitConfiguration(enable=True),
                python_version=min_python,
                generate=[
                    jgc.GenerateItem(
                        source=str(tmp / name),
                        destination=str(write_dir / f"{mod}.py"),
                        root_name="Document",
                    )
                    for mod, (name, _) in schemas.items()
                ],
            )

            with redirect_stdout(io.StringIO()):
                process_config(cfg, [])

        # https://github.com/sbrunner/jsonschema-gentypes/issues/1378
        for generated in cfg["generate"]:
            path = Path(generated["destination"])
            code = path.read_text()
            code = code.replace("\\", r"\\")
            path.write_text(code)
