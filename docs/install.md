# Install

Python 3.12+. The command is `sensorium`.

From PyPI, once published:

    uv pip install sensorium-trace

From git, which works today:

    uv pip install "sensorium-trace @ git+https://github.com/bricelancasterwcp-sudo/sensorium"

Dev checkout:

    uv pip install -e ".[dev]"

The import package and the CLI stay `sensorium`. The name `sensorium` on
PyPI and on npm belongs to unrelated projects.

The TypeScript recorder publishes as the npm package `sensorium-trace`
(Node 24). A Python install ships its sources inside the wheel at
`sensorium/_typescript`. Install its npm dependency with `npm ci` in that
directory. From a checkout:

    npm ci --prefix typescript

The npm package does not replace the `sensorium` CLI. Traces still report
the recorder as `sensorium-ts`.
