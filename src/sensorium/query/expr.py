"""A restricted predicate language over CAPTURED values.

WHAT THIS IS NOT
----------------
It is not `eval`. Nothing here executes program code, reads an attribute,
subscripts, imports, or touches a live object. The inputs are the primitives
`capture_value` wrote into a trace database; the operations are one
comparison, `and`/`or`/`not`, unary minus, five arithmetic operators and
`len(name)`. Everything else -- attributes, subscripts, calls other than
`len`, comprehensions, lambdas, f-strings, `is`/`in`, chained comparisons,
`**`, and every dunder path out of a literal -- is refused at COMPILE time,
before a single site is read. The refusal is compile-time on purpose: a
malformed or hostile expression then fails once, on the command line, rather
than once per site or (worse) not at all.

The restriction is deliberately a real boundary and not a happy accident of
the input types. Reading captured primitives means there is nothing to escape
*to* today; a boundary that only holds because of what happens to be in the
dict is one refactor away from being `eval`, so it is enforced structurally
and tested as a boundary.

WHY A NAME CAN FAIL TO EVALUATE, AND WHY THE REASON MATTERS
-----------------------------------------------------------
A site where the predicate could not be applied is NOT a site where the
predicate was false, and the four ways it can fail send a reader to four
different fixes:

  * OUT_OF_SCOPE -- the name is not bound here. Either it is not bound *yet*
    (or has gone out of scope again, via `del` or the implicit unbind that
    ends `except E as e:`), or this run never recorded that frame's locals at
    all. Only the second is fixed by re-recording with `--focus`, and
    `watch_cmd` tells the two apart before it suggests anything.
  * NO_VALUE -- the name IS bound, to something `capture_value` could only
    record as a type and a repr. Refocusing cannot help; an object has no
    comparable value to record.
  * CONTAINER -- bound to a list/tuple/set/dict, whose length was recorded
    and whose contents were only sampled. `len(name)` works; comparing the
    bare name does not.
  * CLIPPED -- bound to a string longer than the capture cap, so what the
    trace holds is a PREFIX. Comparing a prefix, or taking its length, is a
    claim about characters that were never recorded.

Collapsing any of these into a silent False would let "I could not check"
read as "the invariant held". That is the failure this whole module exists to
prevent, so the reason travels on the exception and `watch` prints it.

TRUNCATION, AND THE ONE PLACE IT DOES NOT BITE
----------------------------------------------
`trunc` on a container capture means the SAMPLE was capped, or the depth was
-- never the length: `_capture_sized` writes `len(obj)` before any cap is
applied. So `len(name)` over a truncated container is exact, and this module
never reads `sample` at all (a depth-capped capture omits that key entirely).
A clipped *string* is the real truncation case, and it is refused.
"""
import ast
import operator

# Why a name the predicate needs has no usable value at some site. `NAME` is
# substituted with the actual name when the message is rendered.
OUT_OF_SCOPE = "not in scope at this site"
NO_VALUE = "recorded as an object, which has no comparable value"
CONTAINER = "recorded as a container; compare its length with len(NAME)"
CLIPPED = "recorded truncated, so the trace does not hold the whole value"
NO_LENGTH = "recorded as a value that has no length"


class ExprError(Exception):
    """Not in this language. Always raised at compile time."""


class NotCaptured(Exception):
    """A name the predicate needs has no usable captured value at this site.

    Never a verdict. Callers count these and report them; the one thing they
    must not do is treat them as the predicate having come back False.
    """

    def __init__(self, name: str, reason: str = OUT_OF_SCOPE) -> None:
        super().__init__(f"{name}: {reason.replace('NAME', name)}")
        self.name = name
        self.reason = reason


class EvalError(Exception):
    """The predicate is well-formed but could not be applied to these values.

    `'five' > 3` and `x / 0` are not misses -- nothing was decided at all.
    Kept apart from `NotCaptured` because the fix is different: the capture is
    fine, the predicate does not fit the data.
    """

    def __init__(self, cause: BaseException) -> None:
        super().__init__(f"{type(cause).__name__}: {cause}")
        self.cause = cause


class _Marker:
    """A singleton with a readable repr, so a leak into output is obvious."""
    __slots__ = ("_label",)

    def __init__(self, label: str) -> None:
        self._label = label

    def __repr__(self) -> str:
        return self._label


NOT_CAPTURED = _Marker("<NOT_CAPTURED>")
TRUNCATED = _Marker("<TRUNCATED>")


class _Sized:
    """A container recorded only by its length. `len()` works; nothing else."""
    __slots__ = ("n",)

    def __init__(self, n: int) -> None:
        self.n = n

    def __repr__(self) -> str:
        return f"<len {self.n}>"


_CMP = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt,
        ast.GtE: operator.ge, ast.Eq: operator.eq, ast.NotEq: operator.ne}
_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Mod: operator.mod}
# The comparisons that have a boundary to approach. `==`/`!=` do not: the
# distance from `a == b` to true is not a number a reader can act on.
_ORDERING = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)
# Raised by applying a legal operator to captured values of the wrong shape.
# Caught and re-raised as EvalError so a site can be counted, never crashed on.
_ARITH = (TypeError, ZeroDivisionError, OverflowError, ValueError)


def resolve(v: dict):
    """One capture -> a usable value, or a marker saying why not.

    Markers rather than exceptions because a caller folds these into an
    environment long before any predicate looks at them: `env[name]` present
    but NOT_CAPTURED means "in scope, no value", which is a different fact
    from the name being absent, and both have to survive the fold.
    """
    k = v.get("k")
    if k in ("num", "bool"):
        return v["v"]
    if k == "str":
        # What the trace holds is a prefix of the real string. It is not the
        # value and must not be compared as if it were.
        return TRUNCATED if v.get("trunc") else v["v"]
    if k == "none":
        return None
    if k in ("seq", "map"):
        # `len` is exact even here: it is written before any cap is applied,
        # and `trunc` on a container means the sample (or the depth) was cut.
        return _Sized(v["len"])
    return NOT_CAPTURED


# -- compiling -------------------------------------------------------------
def _validate_len(node: ast.Call) -> None:
    if not (isinstance(node.func, ast.Name) and node.func.id == "len"):
        raise ExprError("the only call allowed is len(name)")
    if node.keywords or len(node.args) != 1:
        raise ExprError("len takes exactly one positional argument")
    if not isinstance(node.args[0], ast.Name):
        raise ExprError("len's argument must be a plain name, as in len(buf)")


def _validate(node) -> None:
    if isinstance(node, ast.Expression):
        _validate(node.body)
    elif isinstance(node, ast.Constant):
        if not (isinstance(node.value, (int, float, str, bool))
                or node.value is None):
            raise ExprError(f"unsupported constant {node.value!r}")
    elif isinstance(node, ast.Name):
        # `len` reaches here only as a BARE name -- `_validate_len` checks the
        # callee itself and never recurses into it. Left alone, `len > 1`
        # would compile to a lookup for a variable no capture ever holds and
        # be reported as "not in scope", sending a reader after a builtin.
        if node.id == "len":
            raise ExprError("`len` is only allowed as len(name), as in "
                            "len(buf) > 3")
    elif isinstance(node, ast.Call):
        _validate_len(node)
    elif isinstance(node, ast.Compare):
        if len(node.ops) != 1:
            raise ExprError("chained comparisons are not allowed; write one "
                            "comparison, or join two with `and`")
        if type(node.ops[0]) not in _CMP:
            raise ExprError("only < <= > >= == != are allowed as comparisons")
        _validate(node.left)
        _validate(node.comparators[0])
    elif isinstance(node, ast.BoolOp):
        for v in node.values:
            _validate(v)
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op,
                                                     (ast.Not, ast.USub)):
        _validate(node.operand)
    elif isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        _validate(node.left)
        _validate(node.right)
    else:
        raise ExprError(f"unsupported syntax: {type(node).__name__}")


def compile_expr(src: str) -> "Expr":
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError as e:
        raise ExprError(f"not a valid expression: {e.msg}") from None
    _validate(tree)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names.discard("len")          # the callee of a validated len(name) call
    return Expr(tree, names, src)


def _is_real(x) -> bool:
    """A number a margin can be measured against. `True` is not one: bools
    compare as 0/1 and would report a distance of 1 from a boundary they have
    no relationship to."""
    return isinstance(x, (int, float)) and not isinstance(x, bool)


class Expr:
    """A compiled predicate. `names` is every name it may need."""

    def __init__(self, tree: ast.Expression, names: set[str],
                 src: str) -> None:
        self._tree = tree
        self.names = names
        self.src = src

    @property
    def has_boundary(self) -> bool:
        """Whether `margin` can ever return a number for this predicate."""
        node = self._tree.body
        return (isinstance(node, ast.Compare)
                and type(node.ops[0]) in _ORDERING)

    def eval(self, env: dict) -> bool:
        try:
            return bool(self._eval(self._tree.body, env))
        except _ARITH as e:
            raise EvalError(e) from None

    def margin(self, env: dict) -> float | None:
        """How far this site was from the boundary, or None if there is none.

        Defined only for a single numeric ordering comparison at the top: that
        is the only shape where "distance to the boundary" is a number a
        reader can rank sites by.
        """
        if not self.has_boundary:
            return None
        node = self._tree.body
        try:
            lhs = self._eval(node.left, env)
            rhs = self._eval(node.comparators[0], env)
        except (NotCaptured, *_ARITH):
            return None
        return abs(lhs - rhs) if _is_real(lhs) and _is_real(rhs) else None

    # -- evaluation --------------------------------------------------------
    def _eval(self, node, env):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return _name(node.id, env)
        if isinstance(node, ast.Call):            # validated: len(name)
            return _length(node.args[0].id, env)
        if isinstance(node, ast.Compare):
            return _CMP[type(node.ops[0])](
                self._eval(node.left, env),
                self._eval(node.comparators[0], env))
        if isinstance(node, ast.BoolOp):
            return self._boolop(node, env)
        if isinstance(node, ast.UnaryOp):
            v = self._eval(node.operand, env)
            return (not v) if isinstance(node.op, ast.Not) else -v
        return _BIN[type(node.op)](self._eval(node.left, env),
                                   self._eval(node.right, env))

    def _boolop(self, node: ast.BoolOp, env):
        """Short-circuiting, and that is a correctness property, not speed.

        `False and <uncaptured>` is False; `True or <uncaptured>` is True. The
        trace decides those sites, so refusing them would move a site out of
        "evaluated" and into "could not check" -- inflating the one number a
        reader uses to discount a run that reported no hits. Where the missing
        half really does decide the answer, the refusal still happens.
        """
        decisive = not isinstance(node.op, ast.And)
        for v in node.values:
            if bool(self._eval(v, env)) is decisive:
                return decisive
        return not decisive


def _name(name: str, env: dict):
    val = env.get(name, NOT_CAPTURED)
    if val is NOT_CAPTURED:
        raise NotCaptured(name, NO_VALUE if name in env else OUT_OF_SCOPE)
    if val is TRUNCATED:
        raise NotCaptured(name, CLIPPED)
    if isinstance(val, _Sized):
        raise NotCaptured(name, CONTAINER)
    return val


def _length(name: str, env: dict) -> int:
    val = env.get(name, NOT_CAPTURED)
    if isinstance(val, _Sized):
        return val.n
    if isinstance(val, str):
        return len(val)
    if val is NOT_CAPTURED:
        raise NotCaptured(name, NO_VALUE if name in env else OUT_OF_SCOPE)
    if val is TRUNCATED:
        raise NotCaptured(name, CLIPPED)
    raise NotCaptured(name, NO_LENGTH)
