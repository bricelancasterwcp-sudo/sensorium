"""The field help strings more than one query parser prints.

Seven strings, six of them shared by two commands or more. They live here
rather than beside each `add_argument` because they are the same FACT
said once -- what a run reference is, what `--limit` counts -- and a fact
copied into eight parsers drifts into eight wordings, which a caller
reading a tool table meets side by side.

Imported absolutely (`from sensorium.query import help as qhelp`), so the
module name shadows nothing at any call site.
"""
RUN_HELP = "run id, a unique prefix of one, or `last` (the newest trace)"
RUN_A_HELP = "the first run: " + RUN_HELP
RUN_B_HELP = "the second run: " + RUN_HELP
LIMIT_HELP = "most rows to print"
DEPTH_HELP = "levels of the call tree to print below the root"
PATTERN_HELP = "substring matched against event names and rendered values"
KIND_HELP = "keep events of this kind only"
