import json
from subprocess import CalledProcessError, run
import venv
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Literal

import pytest


HERE = Path(__file__).parent
DATA_DIR = HERE / "data"


def build(
    src_path: Path,
    dest_path: Path,
    *,
    dist_type: Literal["sdist", "wheel"] = "wheel",
    installer: Literal["pip", "uv"] = "uv",
    config_settings: Mapping[str, object] = MappingProxyType({}),
) -> Path:
    from build.util import DefaultIsolatedEnv
    from build import ProjectBuilder

    config_settings = dict(config_settings)
    with DefaultIsolatedEnv(installer=installer) as env:
        builder = ProjectBuilder.from_isolated_env(env, src_path)
        env.install(builder.build_system_requires)
        env.install(builder.get_requires_for_build(dist_type, config_settings))
        return builder.build(dist_type, dest_path, config_settings)


def install(wheel_path: Path, interpreter: Path):
    from installer import install
    from installer.destinations import SchemeDictionaryDestination
    from installer.sources import WheelFile

    try:
        out = run([interpreter, "-c", "import json; import sysconfig; print(json.dumps(sysconfig.get_paths()))"], capture_output=True, check=True).stdout
    except CalledProcessError as e:
        e.add_note(e.stderr.decode("utf-8"))
        raise
    scheme_dict = json.loads(out)

    destination = SchemeDictionaryDestination(
        scheme_dict,
        interpreter=interpreter,
        script_kind="posix",
    )

    with WheelFile.open(wheel_path) as source:
        install(
            source=source,
            destination=destination,
            additional_metadata={},
        )


@pytest.fixture()
def env(tmp_path) -> Path:
    (dist_path := tmp_path / "dist").mkdir()
    (env_path := tmp_path / "env").mkdir()
    wheel_path = build(DATA_DIR / "test-pkg", dist_path)
    venv.EnvBuilder(symlinks=True).create(env_path)
    install(wheel_path, env_path / "bin/python")
    return env_path


def test_basic(env):
    print(env)
