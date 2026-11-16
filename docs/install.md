# Install

Python 3.12+. The command is `sensorium`.

    pip install sensorium-trace
    uv tool install sensorium-trace

TypeScript recorder (Node 24):

    npm install sensorium-trace

These resolve once the packages are on the indexes. The name `sensorium` on
PyPI and on npm belongs to unrelated projects. The publish name is
`sensorium-trace`. The import package and the CLI stay `sensorium`. The npm
package is the recorder library; traces still report the recorder as
`sensorium-ts`.

From git:

    uv pip install "sensorium-trace @ git+https://github.com/bricelancasterwcp-sudo/sensorium"

Dev checkout:

    uv pip install -e ".[dev]"

A Python install also ships the TypeScript recorder sources inside the wheel
at `sensorium/_typescript`. Install its npm dependency with `npm ci` in that
directory. From a checkout:

    npm ci --prefix typescript

The CLI remains the Python `sensorium` command.
