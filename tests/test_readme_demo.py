"""The README demo is a real failing test, recorded and queried as typed.

The transcript at the top of README.md is trimmed from one recording of
`examples/test_shipping.py`. Event ids move; the smoking-gun strings do not.
"""
from pathlib import Path

from tests.helpers import run_cli

REPO = Path(__file__).resolve().parents[1]
README = REPO / "README.md"
DEMO = ["run", "--", "pytest", "examples/test_shipping.py", "-q"]


def test_readme_leads_with_the_shipping_transcript_and_refusal_strings():
    text = README.read_text()
    assert "sensorium run -- pytest examples/test_shipping.py -q" in text
    assert "item_weight -> 1800" in text
    assert "shipping_cost(weight_kg=1800)" in text
    assert "refocus verdict: MATCH" in text
    assert "pip install sensorium-trace" in text
    assert "uv tool install sensorium-trace" in text
    assert "npm install sensorium-trace" in text
    assert "REFUSED:" in text
    assert ("verdict: NOTHING WAS CHECKED -- the predicate could not be "
            "evaluated at any of the N recorded site(s)") in text
    assert ("'hits: 0' here means 'could not evaluate', NOT "
            "'the invariant held'") in text
    assert "verdict: DIVERGED at causal step N" in text
    assert "refocus verdict: DIVERGED --" in text
    assert "refocus verdict: REFUSED --" in text
    assert "verdict: REFUSED -- cannot issue a MATCH/DIVERGED verdict" in text


def test_readme_install_leads_with_indexes_and_keeps_git_as_fallback():
    text = README.read_text()
    install = text.split("## Install", 1)[1]
    git = install.find("git+https://github.com/bricelancasterwcp-sudo/sensorium")
    pypi = install.find("pip install sensorium-trace")
    npm = install.find("npm install sensorium-trace")
    assert pypi != -1 and npm != -1 and git != -1
    assert pypi < git and npm < git
    assert "The CLI command is `sensorium`" in install


def test_the_shipping_demo_fails_because_grams_enter_as_kg(tmp_path):
    store = tmp_path / "store"
    rec = run_cli(DEMO, cwd=REPO, sensorium_dir=store)
    assert rec.returncode == 1, rec.stdout + rec.stderr
    assert "run: " in rec.stdout
    assert "AssertionError: assert 5569.0 == 74.5" in rec.stdout

    exc = run_cli(["exceptions", "last"], cwd=REPO, sensorium_dir=store)
    assert exc.returncode == 0, exc.stdout + exc.stderr
    assert "AssertionError" in exc.stdout
    assert "propagated (handler not in traced code)" in exc.stdout

    flow = run_cli(["flow", "last", "--value", "1800"],
                   cwd=REPO, sensorium_dir=store)
    assert flow.returncode == 0, flow.stdout + flow.stderr
    assert "item_weight -> 1800" in flow.stdout
    assert "shipping_cost(weight_kg=1800)" in flow.stdout

    ref = run_cli(
        ["refocus", "last", "--focus", "examples.shipping:shipping_cost",
         "--compact"],
        cwd=REPO, sensorium_dir=store)
    assert ref.returncode == 0, ref.stdout + ref.stderr
    assert ("refocus verdict: MATCH -- every recorded thread produced the "
            "identical CALL/RETURN/RAISE/HANDLED sequence") in ref.stdout
