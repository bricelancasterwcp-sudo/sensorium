"""The `flow` program shapes, and the helpers that read a flow screen.

Split out of `programs.py` at that file's own `# -- flow shapes` banner when
it reached the 800-line ceiling. Same split as `watch_programs.py` and
`refocus_programs.py`, for the same reason: each source here exists to
produce ONE recorded shape -- an aliased dict handed between frames, an
address a run reuses -- and the comment explaining that shape belongs with
the source, not in the middle of the test that reads it.
"""
from sensorium import paths
from sensorium.store.reader import Trace

# -- flow shapes -----------------------------------------------------------
# Shared by `test_flow.py` (equality) and `test_flow_identity.py` (identity).
GRAMS = """
def shipping_cost(weight_kg):
    return 4.0 + 2.5 * weight_kg

def item_weight(item):
    return item["grams"]

def order_total(items):
    goods = sum(i["price"] for i in items)
    ship = sum(shipping_cost(item_weight(i)) for i in items)
    return round(goods + ship, 2)

def main():
    items = [{"name": "mug", "price": 12.0, "grams": 400},
             {"name": "kettle", "price": 49.0, "grams": 1800}]
    print("total:", order_total(items))

if __name__ == "__main__":
    main()
"""

ALIAS = """
def make_default():
    return {"retries": 3, "timeout": 30}

def derive_sandbox(cfg):
    sandbox = cfg
    sandbox["timeout"] = 1
    return sandbox

def main():
    prod = make_default()
    sand = derive_sandbox(prod)
    print("prod timeout:", prod["timeout"])

if __name__ == "__main__":
    main()
"""

def open_trace(run_id) -> Trace:
    return Trace.open(paths.find_trace(run_id))


def flow_rows(out: str) -> list[str]:
    """The sighting lines: `  e<id> KIND ...   [role]`."""
    return [ln.strip() for ln in out.splitlines()
            if ln.startswith("  e") and ln.rstrip().endswith("]")]


def obj_captures(trace) -> list[tuple[int, int, str]]:
    """(event id, oid, type) for every top-level `obj` capture recorded.

    Deliberately re-derived here from the payloads rather than through
    flow_cmd, so the fixture's address collisions are established
    independently of the code under test.
    """
    out = []
    for e in trace.events():
        p = e.payload or {}
        vals = list(p.get("args", {}).values()) + list(
            p.get("deltas", {}).values())
        if p.get("value") is not None:
            vals.append(p["value"])
        for v in vals:
            if v.get("k") == "obj":
                out.append((e.id, v["oid"], v["type"]))
    return out


def interleaved_address(trace, a: str, b: str):
    """The address that hosted an `a`, then a `b`, then an `a` again.

    Returns (address, [(event id, type), ...] at it). Three objects minimum,
    one address: the shape that makes `oid` alone a false identity.
    """
    by_oid: dict[int, list] = {}
    for eid, oid, typ in obj_captures(trace):
        by_oid.setdefault(oid, []).append((eid, typ))
    for oid, seq in by_oid.items():
        types = [t for _e, t in seq]
        if a not in types or b not in types:
            continue
        rest = types[types.index(a):]
        if b in rest and a in rest[rest.index(b):]:
            return oid, seq
    raise AssertionError(
        f"this test needs one address hosting {a}, then {b}, then {a} again; "
        f"CPython allocated {by_oid}")


def flow_shown_ids(out: str) -> set[int]:
    """The event ids actually listed as sightings."""
    return {int(r.split()[0][1:]) for r in flow_rows(out)}
