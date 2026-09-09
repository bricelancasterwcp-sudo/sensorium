# Sourced by the shell instruments in this directory: the lens string, and
# the two helpers that keep their JSON in the record's schema.
#
# Not executable and not a program -- `. "$(dirname "$0")/lens.sh"`.
ACCEPT_LENS="$(cat "$(dirname "${BASH_SOURCE[0]}")/LENS.txt")"

# json_escape <string>  -- a bare string as a JSON string body (no quotes).
json_escape() {
  python3 -c 'import json,sys; sys.stdout.write(json.dumps(sys.argv[1])[1:-1])' "$1"
}

# refuse <message>  -- name the bad call on stderr and exit 2.
refuse() { printf '%s\n' "$1" >&2; exit 2; }
