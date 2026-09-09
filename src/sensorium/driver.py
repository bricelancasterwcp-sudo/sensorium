"""Which `cargo-sensorium` this box will use, resolved in ONE place.

The rule is two lines long and was written out three times: in
`query/refocus_rust.py` (what a `refocus` re-runs with), in
`corpus/run_corpus.py` (what a corpus case records with), and in
`tests/test_focus_refusal.py` (what its skip is decided on). They agreed,
and a parametrised test held them to it -- but agreement kept by a test is
agreement that has to be re-established after every edit, and the three
answers have to be the SAME answer or a corpus case records with one binary
and its `refocus` question re-runs with another.

It lives under `src/sensorium/` because that is the only one of the three
trees all three can reach. `corpus/` is a development tree beside the
package and is not in the wheel (`pyproject.toml` packages `src/sensorium`
only), so a query command importing it would work from a checkout and fail
from an install; `tests/` is no better. The dependency runs the other way
here -- the corpus and the suite already require `sensorium` to be
importable, since the corpus records by running `python -m sensorium`.
"""
import os
import shutil

#: The variable that names the driver, and the only one. CI's `rust` job
#: builds a binary and sets it; so does a developer with a release build on
#: a second disk. Written down here so a reader looking for "how do I point
#: this at my build" finds one name and not three copies of it.
ENV_VAR = "SENSORIUM_CARGO_SENSORIUM"


def cargo_sensorium() -> str | None:
    """The `cargo-sensorium` binary to use, or None when there is none.

    `SENSORIUM_CARGO_SENSORIUM` first, then PATH. An EMPTY variable is not a
    driver -- `or` and not a presence test, so `SENSORIUM_CARGO_SENSORIUM=`
    falls through to PATH rather than resolving to `""` and failing later at
    exec time with a message about an empty command.

    None is not an error. It is the ordinary state of the Python CI matrix,
    which has no Rust toolchain: the corpus reports the cases it cannot
    record as skipped BY NAME, and `refocus` refuses a Rust re-run with a
    sentence that says what is missing. Both of those readings need to be
    told "no driver" rather than handed a path that does not exist.

    `shutil.which` is called through the module (never `from shutil import
    which`) so a test can patch it where every caller sees the patch.
    """
    return os.environ.get(ENV_VAR) or shutil.which("cargo-sensorium")
