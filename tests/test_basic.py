from subprocess import run
import sys
from collections.abc import Generator, Mapping
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


def install(wheel_path: Path):
    import sysconfig

    from installer import install
    from installer.destinations import SchemeDictionaryDestination
    from installer.sources import WheelFile

    destination = SchemeDictionaryDestination(
        sysconfig.get_paths(),
        interpreter=sys.executable,
        script_kind="posix",
    )

    with WheelFile.open(wheel_path) as source:
        install(
            source=source,
            destination=destination,
            additional_metadata={},
        )


@pytest.fixture()
def test_pkg(tmp_path) -> Generator[str, None, None]:
    (dist_path := tmp_path / "dist").mkdir()
    wheel_path = build(DATA_DIR / "test-pkg", dist_path)
    install(wheel_path)
    yield
    run(
        ["uv", "pip", "uninstall", f"--python={sys.executable}", "test-pkg"], check=True
    )
    del sys.modules["test_pkg"]


def test_basic(test_pkg):
    import test_pkg as _

    from importlib.metadata import version

    assert version("test_pkg") == "0.0.1"


def test_inverse():
    with pytest.raises(ImportError):
        import test_pkg
