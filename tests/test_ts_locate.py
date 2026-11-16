"""Where `sensorium ts` finds the Node package.

A checkout (and an editable install of one) keeps it at `typescript/` beside
`src/`. A wheel, which is what `pip install git+https://...` builds, has no
such directory: the sources ride inside the installed package at
`sensorium/_typescript`. `SENSORIUM_TS_PKG` still wins when it is set, and an
empty value is not a location.
"""
from __future__ import annotations

import os
import subprocess
import venv
from pathlib import Path

import pytest

from sensorium.ts.pkg import ENV_VAR, PackageError, check, locate

ROOT = Path(__file__).resolve().parents[1]


def test_a_checkout_locates_typescript_beside_src(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    found = locate()
    assert found == (ROOT / "typescript").resolve()
    assert (found / "package.json").is_file()
    assert (found / "src" / "rt.mjs").is_file()


def test_an_empty_override_falls_through_to_the_checkout(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "")
    assert locate() == (ROOT / "typescript").resolve()


def test_an_override_is_the_location_even_when_the_checkout_exists(monkeypatch, tmp_path):
    monkeypatch.setenv(ENV_VAR, str(tmp_path))
    assert locate() == tmp_path


def test_a_wheel_install_locates_the_shipped_package(tmp_path):
    """Non-editable install, the shape `git+https` produces.

    Built from an sdist so the wheel is not reading the checkout's
    `typescript/` at package time only: the sdist has to carry the Node
    sources, and the wheel built from that sdist has to lay them down at
    `sensorium/_typescript`. The build runs in its own venv so this test
    does not upgrade the interpreter that is running the suite.
    """
    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    py = env_dir / "bin" / "python"
    subprocess.run([str(py), "-m", "pip", "install", "--upgrade", "pip", "build"], check=True)
    dist = tmp_path / "dist"
    subprocess.run(
        [str(py), "-m", "build", "--sdist", "--outdir", str(dist)],
        cwd=ROOT,
        check=True,
    )
    sdist = next(dist.glob("sensorium_trace-*.tar.gz"))
    wheel_dir = tmp_path / "wheels"
    subprocess.run(
        [str(py), "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(wheel_dir), str(sdist)],
        check=True,
    )
    wheel = next(wheel_dir.glob("sensorium_trace-*.whl"))
    subprocess.run([str(py), "-m", "pip", "install", "--no-deps", str(wheel)], check=True)
    script = r"""
import sensorium.ts.pkg as p
loc = p.locate()
assert (loc / "package.json").is_file(), loc
assert (loc / "src" / "rt.mjs").is_file(), loc
assert loc.name == "_typescript", loc
try:
    p.check(loc)
except p.PackageError as e:
    text = str(e)
else:
    raise SystemExit("check() should refuse before npm ci")
assert "npm ci" in text, text
assert str(loc) in text, text
"""
    # A parent PYTHONPATH that points at a checkout would make this venv
    # import that tree instead of the wheel it just installed.
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    proc = subprocess.run(
        [str(py), "-c", script], cwd=tmp_path, capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_check_names_npm_ci_when_node_modules_is_absent(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    pkg = locate()
    # The checkout's node_modules may be installed. The message shape is what
    # a wheel hits; assert it against a directory that has a package.json and
    # no magic-string, which is the wheel's layout before `npm ci`.
    if (pkg / "node_modules" / "magic-string").is_dir():
        pytest.skip("checkout node_modules is installed; the wheel test covers check()")
    with pytest.raises(PackageError, match="npm ci"):
        check(pkg)
