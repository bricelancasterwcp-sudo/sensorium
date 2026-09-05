# Rung 3 — Borrow Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the escape test's `&e` exemption so an arm that hands a borrow to a function and KEEPS the call's product reads `arm_ambiguous`; give the chain machine's `err` close the text-preferring hop search; and MEASURE the repair where its shapes execute — a `--workspace` E6 arm with no `--lib`, beside a control under the pre-repair driver that shows the arm reaches the shape.

**Architecture:** One transformer change in `rust/sensorium-transform/src/escape.rs` (the borrow exemption becomes a rule about dropped call sites), one converter change in `rust/cargo-sensorium/src/convert/chains/mod.rs::close_frame` (prefer the held chain whose text the RETURN carries), two corpus cases, and a sibling acceptance runner `rust/tests/acceptance_e6q.py` that reuses the committed E6‴ tooling for three arms (A, WS, WS0), a BEFORE/AFTER arm-manifest diff, E6-again′, E7⁗ and E0‴. Pre-registration is byte-locked before any number is read.

**Tech Stack:** Rust 1.96.0 (pinned; `syn` 2 full/visit), Python 3.12+ (stdlib reader), pytest, the corpus and acceptance harnesses under `rust/tests/` and `tests/`, the bloomery clone on `/mnt/extra`.

**Spec:** `docs/superpowers/specs/2026-09-05-sensorium-rung3-borrow-repair-design.md` (B1–B8, §2 the rule, §3 the hop, §4 the pre-registration — the binding design; committed at `1a235cc`), arguing from `docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md` (R2, R7/§2a, R15, R16). Rigor: `~/.claude/skills/rigorous-experiments/SKILL.md`. Prior records never touched: `docs/superpowers/acceptance/2026-09-0{2,3,4,5}-*`.

## Global Constraints

- **Branch** `feat/rung3-borrow-repair` from `main` @ `d1b1b57` (exists; design committed at `1a235cc`). PR against `main`; merge is Brice's. Never push `main`.
- **`/home/brice/workspace/bloomery` is read-only, forever.** The only bloomery built or checked out is the clone `/mnt/extra/sensorium-rung2/bloomery` (HEAD detached at `e209ed9`).
- **Every artifact set on the second disk**: workspace `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target`; HEAD-driver acceptance target `/mnt/extra/sensorium-rung2/bloomery-target`; **control (base-driver) target `/mnt/extra/sensorium-rung2/bloomery-target-control`**; corpus target `/mnt/extra/sensorium-rung2/corpus-target-e6q` (fresh for T5); probe target `/mnt/extra/sensorium-rung2/probe-target`; base worktree `/mnt/extra/sensorium-rung2/base-d1b1b57` with target `/mnt/extra/sensorium-rung2/rust-target-base`; trace store `SENSORIUM_DIR=/mnt/extra/sensorium-rung2/sensorium-dir/e6q`. Root disk ≈ 12 GB free: never a default `target/`. ONE cargo invocation at a time per target.
- **No box-local path in any committed file** except the acceptance record's lens rows and this plan. Tests read the clone only from `SENSORIUM_BLOOMERY_CLONE`, skipping by name when unset.
- **`-D warnings` clean** on 1.96.0 (`cd rust && cargo clippy --workspace --all-targets -- -D warnings`, `cargo fmt --check`); the rustc oracle for goldens stays `-D warnings` with empty stderr.
- **Every new or changed test is mutation-tested** (the mutation and its failing output in the task report); mutant runs under `setsid` + timeout + kill by pgid + `ps -p`; never `pkill -f`; Python mutants purge `__pycache__` with `PYTHONDONTWRITEBYTECODE=1`.
- **Pre-registration byte-locked before any number is read** (T4's last commits, §1 ALONE); T5 refuses to run if §1 differs; a completed measurement is never re-rolled; a miss is a STOP with its number. **No code change after the lock**: a residual found by review after the numbers is recorded (design R16, `rust/HONESTY-BLIND-SPOTS.md`, `docs/CARRIED-DEBT.md`), not repaired.
- **No file over 800 lines** (`rust/HONESTY.md` is at 796: if T6's edit grows it, §1 moves to `rust/HONESTY-OUTCOMES.md` first; `rust/tests/mechanics.sh` at 795 is not touched).
- **The line count of every instrumented file is unchanged by the transform** (`splice::check_line_count`); this slice adds no fragment.
- **Versions** (B6): `sensorium-transform` 0.3.1, `cargo-sensorium` 0.3.1 (`DRIVER_VERSION` in `rust/cargo-sensorium/src/driver.rs` and its pins at `driver.rs:724`, `driver.rs:757`, `tests/driver_smoke.rs:125`), `sensorium-rt` stays 0.3.0, Python 0.8.1 (`pyproject.toml`). Grep before writing.
- **One implementer per worktree at a time**; every commit by explicit path (never `git add -A`); `git show --stat HEAD` read after every commit; commit messages end with the two trailer lines
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn`
- Every shell command starts `cd /home/brice/workspace/sensorium &&`. Rust commands run from `rust/` with the workspace target set. The Python venv is `.venv/bin/python`; pytest is `.venv/bin/python -m pytest`.
- Ledger: `.superpowers/sdd/2026-09-05-sensorium-rung3-borrow-repair/progress.md` (gitignored) — every ruling, every measured number that feeds §1, every commit sha.

---

## Decisions carried from the design

B1 = the dropped-call-site rule (§2 of the design); B2 = blind spot 23 (d), pinned by a row; B3 = the exit-hop text preference (§3); B4/B5 = the arms and what the control licenses (§4); B6 = versions; B7 = docs by dated pointer; B8 = process. A task that needs a decision the design lacks stops and the controller rules (ledger).

## Pre-registration — §1 of `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md`

The table is design §4 verbatim, with `<N1>`..`<N5>` filled from the ledger (T0's BEFORE census, T1's AFTER census on the clone) before T4 commits §1 ALONE. T5's runner refuses to start unless `awk '/^## 1/,/^## 2/'` of the working tree equals the locked commit's bytes. Lens rows and "Reported without a gate" as in design §4.

## File Structure

- **Transformer**: modify `rust/sensorium-transform/src/escape.rs` (the walker: `visit_stmt`, `walk_dropped_call`, `visit_arg`, `is_shared_borrow_of_name`, `is_wild`; delete the `visit_expr_reference` override; `format_arg_escapes` learns the dropped treatment; module docs), `rust/sensorium-transform/src/arms.rs` (test rows only, `mod tests`). Goldens under `tests/golden/` are expected unchanged (the three `note(&e);` shapes are statement-form).
- **Converter**: modify `rust/cargo-sensorium/src/convert/chains/mod.rs` (`close_frame`, module doc, `close_frame` doc), `rust/cargo-sensorium/src/convert/chains/tests.rs` (+1 test), `rust/cargo-sensorium/tests/convert_errflow_chains.rs` (+1 test).
- **Corpus**: create `corpus/rust/err_borrowed_into_value/{Cargo.toml,src/main.rs,questions.yaml}`, `corpus/rust/keep_first_error/{Cargo.toml,src/main.rs,questions.yaml}`; modify `corpus/rust/README.md`.
- **Acceptance tooling**: modify `rust/tests/acceptance_phases_rung3.py` (`phase_e6prime` gains `tail`); create `rust/tests/acceptance_e6q.py`, `rust/tests/acceptance_schema_e6q.py`, `rust/tests/render_e6q.py`, `tests/test_acceptance_e6q.py`; create `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md` (§1 alone, then §2–§5 at T5) and its `.results.json` (T5).
- **Docs/versions** (T6): `rust/HONESTY.md` §11, `rust/HONESTY-BLIND-SPOTS.md` item 23, `rust/HONESTY-INDEX.md`, `docs/TRACE-FORMAT.md` §5, the rung-3 design (dated pointers), `CHANGELOG.md`, `docs/CARRIED-DEBT.md`, `pyproject.toml`, `rust/sensorium-transform/Cargo.toml`, `rust/cargo-sensorium/Cargo.toml` + the three `DRIVER_VERSION` pins, `rust/Cargo.lock`.

---

### Task 0: Baseline, base driver, BEFORE census

**Files:**
- Modify: `.superpowers/sdd/2026-09-05-sensorium-rung3-borrow-repair/progress.md` (ledger; gitignored)
- No committed file changes.

**Interfaces:**
- Produces: the base driver binary `/mnt/extra/sensorium-rung2/rust-target-base/release/cargo-sensorium` (built from `d1b1b57`) with its sha256 in the ledger; the ledger's **census BEFORE** block (`arm sites`, `arms escaped`, `arms handled`, `arms propagate`) — T4's `<N1>`, `<N3>`, `<N5>`; the baseline test counts.

- [ ] **Step 1: Confirm the tree and record the baseline**

Run:
```bash
cd /home/brice/workspace/sensorium && git status --porcelain && git log --oneline -2 && \
cd rust && CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target cargo test --workspace 2>&1 | grep -E "^test result|FAILED" && \
CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target cargo clippy --workspace --all-targets -- -D warnings 2>&1 | tail -2 && cargo fmt --check && echo FMT-OK
```
Expected: porcelain empty; HEAD `1a235cc` on `feat/rung3-borrow-repair`; every `test result: ok`; clippy finishes with no error; `FMT-OK`. Record the per-crate pass counts in the ledger.

- [ ] **Step 2: Python baseline with the driver**

Run:
```bash
cd /home/brice/workspace/sensorium && SENSORIUM_CARGO_SENSORIUM=/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium \
CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/corpus-target PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q 2>&1 | tail -3
```
Expected: the 0.8.0 counts (≈1153 passed, 1 known red at most — the HANDLED-fingerprint mutant pin is the only red the rung-3 close-out left; anything else is a finding: stop and record). Record the counts.

- [ ] **Step 3: Build the base driver from `d1b1b57` in a worktree on the second disk**

Run:
```bash
cd /home/brice/workspace/sensorium && git worktree add --detach /mnt/extra/sensorium-rung2/base-d1b1b57 d1b1b57 && \
cd /mnt/extra/sensorium-rung2/base-d1b1b57/rust && CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target-base cargo build --release -p cargo-sensorium 2>&1 | tail -2 && \
sha256sum /mnt/extra/sensorium-rung2/rust-target-base/release/cargo-sensorium && \
/mnt/extra/sensorium-rung2/rust-target-base/release/cargo-sensorium sensorium --version 2>/dev/null || /mnt/extra/sensorium-rung2/rust-target-base/release/cargo-sensorium --version
```
Expected: `Finished release`; a sha256; the version line says `cargo-sensorium 0.3.0`. Ledger: the sha, the worktree path, `git -C /mnt/extra/sensorium-rung2/base-d1b1b57 rev-parse HEAD` = `d1b1b57…`. Never edit that worktree.

- [ ] **Step 4: The BEFORE census on the clone (the current = pre-repair transformer)**

Run:
```bash
cd /home/brice/workspace/sensorium/rust && SENSORIUM_BLOOMERY_CLONE=/mnt/extra/sensorium-rung2/bloomery \
CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target cargo test -p sensorium-transform --test census census_on_the_bloomery_clone -- --nocapture 2>&1 | grep -E "clone root|arm sites|arms (propagate|panic|escaped|handled)|line moves|test result"
```
Expected: `arm sites: 225`, `arms escaped: 121`, `arms handled: 65`, `arms propagate: 39` (E6‴ §5.6's numbers — if they differ, the clone moved: stop, `git -C /mnt/extra/sensorium-rung2/bloomery status`, record). Ledger block **census BEFORE** with all four numbers and the clone HEAD.

- [ ] **Step 5: Ledger + report**

Write the numbers, shas and paths into the ledger's `## Baseline` section; task report to the controller. No commit (nothing tracked changed).

---

### Task 1: Transformer — the `&e` rule (design B1/B2, §2)

**Files:**
- Modify: `rust/sensorium-transform/src/escape.rs` (walker + `format_arg_escapes` + module docs)
- Modify: `rust/sensorium-transform/src/arms.rs` (`mod tests` rows only)
- Test: `rust/sensorium-transform/src/arms.rs` (`class_of` rows), `rust/sensorium-transform/tests/golden*.rs` (expected unchanged), `tests/census.rs` (clone; AFTER numbers)

**Interfaces:**
- Consumes: `arms::{strip, Body}`, `Class`, `LOGGING_MACROS` (unchanged), `bare_name`, `tokens_mention*` (unchanged).
- Produces: `escape::escapes(body, names) -> bool` unchanged in signature; the ledger's **census AFTER** block (`arms escaped`, `arms handled`, `arm sites`) — T4's `<N2>`, `<N4>`.

- [ ] **Step 1: Write the failing rows** — add to `rust/sensorium-transform/src/arms.rs` `mod tests` (beside `a_plain_closure_keeps_both_exemptions`):

```rust
    #[test]
    fn a_borrow_is_exempt_only_where_the_borrowing_calls_product_is_dropped() {
        // The 2026-09-05 borrow repair (design B1). The old exemption proved
        // the BORROW could not outlive the arm and said nothing about the
        // call's VALUE: `map_error(&e, ..)` on the bloomery clone returns the
        // failure as a status and body the caller receives (api_v1.rs:396,
        // :515). A `&e` is now exempt only as a direct argument of a call
        // whose product is provably dropped -- a `;` statement, a `let _ =`,
        // or a logging macro's argument.
        for text in [
            // dropped: an expression statement
            "Err(e) => { note(&e); 0 },",
            "Err(e) => { self.report(&e); 0 },",
            "Err(e) => { note(&e, 1, \"x\"); 0 },",
            "Err(e) => { if c { note(&e); } 0 },",
            // dropped: `let _ =`, typed or not
            "Err(e) => { let _ = note(&e); 0 },",
            "Err(e) => { let _: () = note(&e); 0 },",
            // dropped: a logging macro's argument, bare or through one call
            "Err(e) => { println!(\"{}\", &e); 0 },",
            "Err(e) => { println!(\"{}\", render(&e)); 0 },",
            // a plain closure whose BODY drops the product
            "Err(e) => { let c = || { note(&e); }; c(); 0 },",
            // a `move` closure that never names the error leaves the arm alone
            "Err(e) => { let c = move || 1; drop(c); note(&e); 0 },",
        ] {
            assert_eq!(class_of(text), Some(Class::Handled), "{text}");
        }
        for text in [
            // the clone's :396 -- a `let` keeps the product
            "Err(e) => { let (s, v) = map_error(&e, None); json(s, v) },",
            // the clone's api_native shape -- the product is the arm's value
            "Err(e) => map_error(&e),",
            "Err(e) => { let r = describe(&e); r },",
            // nested: `render`'s product is handed on
            "Err(e) => { v.push(render(&e)); 0 },",
            // a condition, a scrutinee: the value flows
            "Err(e) => { if check(&e) { 1 } else { 0 } },",
            "Err(e) => match &e { _ => 0 },",
            // a block tail and a closure tail are not dropped sites
            "Err(e) => { note(&e) },",
            "Err(e) => { let c = || note(&e); c(); 0 },",
            // nested inside the logging argument's own call
            "Err(e) => { println!(\"{}\", wrap(render(&e))); 0 },",
            // `move`: unchanged
            "Err(e) => { thread::spawn(move || note(&e)); 0 },",
        ] {
            assert_eq!(class_of(text), Some(Class::Escaped), "{text}");
        }
    }

    /// Blind spot 23 (d): a callee that STORES a rendering of the borrow
    /// through `&self`, a capture or a global is invisible to a syntactic
    /// rule. This row documents today's reading; it is not a claim that the
    /// reading is right on every tree.
    #[test]
    fn a_dropped_call_that_stores_what_it_is_handed_is_still_handled_and_says_so() {
        assert_eq!(
            class_of("Err(e) => { self.record(&e); 0 },"),
            Some(Class::Handled)
        );
    }
```

Then in the EXISTING `a_plain_closure_keeps_both_exemptions`, move the row `"Err(e) => { let c = || note(&e); c(); 0 },"` out of the Handled list (it is now in the Escaped list above) and add a comment: `// \`|| note(&e)\` moved to the borrow-repair rows on 2026-09-05: a closure TAIL is not a dropped site.`

- [ ] **Step 2: Run the rows to see them fail**

Run: `cd /home/brice/workspace/sensorium/rust && CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target cargo test -p sensorium-transform --lib arms::tests 2>&1 | grep -E "^test |panicked|test result"`
Expected: `a_borrow_is_exempt_only_where_the_borrowing_calls_product_is_dropped` FAILS on the first Escaped row (`let (s, v) = map_error(&e, None)` reads Handled today); the 23 (d) row passes (it pins current behaviour).

- [ ] **Step 3: Implement the rule in `escape.rs`**

Delete the `visit_expr_reference` override entirely (the default walk descends into the borrowed expression, reaches `visit_expr_path`, and escapes). Add to `impl<'ast> Visit<'ast> for EscapeWalk<'_>`:

```rust
    /// The dropped call sites (design B1): an expression statement ending in
    /// `;`, or a `let _ = …;` (typed or not, no `else`). A call or method
    /// call that IS such a statement may take a shared borrow of a bound name
    /// as a direct argument without escaping it: the borrow cannot outlive the
    /// arm, and the call's product dies at the semicolon. Everything else in
    /// the statement -- the callee, the receiver, every other argument, and
    /// anything nested inside an argument -- is walked as usual.
    fn visit_stmt(&mut self, node: &'ast Stmt) {
        let dropped: Option<&'ast Expr> = match node {
            Stmt::Expr(e, Some(_)) => Some(e),
            Stmt::Local(l) => match &l.init {
                Some(init) if init.diverge.is_none() && is_wild(&l.pat) => Some(&init.expr),
                _ => None,
            },
            _ => None,
        };
        match dropped {
            Some(e) if self.walk_dropped_call(e) => {}
            _ => syn::visit::visit_stmt(self, node),
        }
    }
```

and to `impl EscapeWalk<'_>`:

```rust
    /// Walk `f(.., &e, ..)` or `x.f(.., &e, ..)` at a dropped site, exempting
    /// exactly the arguments that are a shared borrow of a bound name. Returns
    /// `false`, having walked nothing, when `e` is not a call at all -- the
    /// caller then walks the statement the ordinary way.
    fn walk_dropped_call(&mut self, e: &'ast Expr) -> bool {
        match strip(e) {
            Expr::Call(c) => {
                self.visit_expr(&c.func);
                for a in &c.args {
                    self.visit_arg(a);
                }
                true
            }
            Expr::MethodCall(m) => {
                self.visit_expr(&m.receiver);
                for a in &m.args {
                    self.visit_arg(a);
                }
                true
            }
            _ => false,
        }
    }

    /// One argument of a dropped call: `&e` is exempt outside a `move`
    /// capture; anything else is walked.
    fn visit_arg(&mut self, a: &'ast Expr) {
        if self.moved == 0 && self.is_shared_borrow_of_name(a) {
            return;
        }
        self.visit_expr(a);
    }

    fn is_shared_borrow_of_name(&self, e: &Expr) -> bool {
        matches!(strip(e), Expr::Reference(r) if r.mutability.is_none() && self.is_name(&r.expr))
    }
```

and a free function:

```rust
/// `_` or `_: T` -- the `let` patterns whose value is dropped by construction.
fn is_wild(p: &Pat) -> bool {
    match p {
        Pat::Wild(_) => true,
        Pat::Type(t) => is_wild(&t.pat),
        _ => false,
    }
}
```

(`use syn::{Expr, ExprPath, Macro, Pat, Stmt};` — extend the import.) The lifetime on `walk_dropped_call`/`visit_arg` is the `Visit<'ast>` lifetime: declare them inside the `impl<'ast> Visit<'ast> for EscapeWalk<'_>` block's sibling `impl<'a> EscapeWalk<'a>` as `fn walk_dropped_call<'ast>(&mut self, e: &'ast Expr) -> bool where Self: Visit<'ast>`; if the borrow checker objects, make them free functions taking `&mut EscapeWalk<'_>` and `&'ast Expr` — the shape is the requirement, not the placement.

In `format_arg_escapes`, after the `bare_name` `continue`, add:

```rust
        // A bare `&e` goes to `format_args!` by reference and the macro's
        // value is `()`: exempt, as the bare name is. A CALL taking `&e` as a
        // direct argument is treated as a dropped call site -- the logging
        // macro prints its product and keeps nothing (design B1 (3)).
        let mut walk = EscapeWalk::new(names);
        if walk.is_shared_borrow_of_name(&expr) {
            continue;
        }
        if !walk.walk_dropped_call(&expr) {
            walk.visit_expr(&expr);
        }
        if walk.escaped {
            return true;
        }
```

replacing the existing `let mut walk = …; walk.visit_expr(&expr); if walk.escaped { return true; }`.

Update the module doc (lines 1–7) and the `visit_expr_reference` doc's content into `visit_stmt`'s: the rule is now "a `&e` is exempt only as a direct argument of a call whose product is dropped", dated 2026-09-05, citing design B1 and blind spot 23 (c)/(d).

- [ ] **Step 4: Run the rows green, then the whole transform crate**

Run: `cd /home/brice/workspace/sensorium/rust && CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target cargo test -p sensorium-transform 2>&1 | grep -E "^test result|FAILED|panicked"`
Expected: every `test result: ok`; the goldens unchanged (if any golden fails, STOP: list the case and the changed `how` in the report — the three `note(&e);` shapes are statement-form and must not move).

- [ ] **Step 5: clippy + fmt + the oracle**

Run: `cd /home/brice/workspace/sensorium/rust && CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target cargo clippy -p sensorium-transform --all-targets -- -D warnings 2>&1 | tail -1 && cargo fmt --check && echo FMT-OK`
Expected: no errors; `FMT-OK`.

- [ ] **Step 6: Mutation-test the rule** (each run under `setsid timeout 600 …`; restore after each; record the failing test name):
  1. In `visit_arg`, delete `self.moved == 0 &&` → `a_move_closure_defeats_both_exemptions` must go red.
  2. In `walk_dropped_call`, make the `_ =>` arm return `true` → the Escaped rows `{ note(&e) }` and `let c = || note(&e); c();` must go red.
  3. In `visit_stmt`, change `Stmt::Expr(e, Some(_))` to `Stmt::Expr(e, _)` → `"Err(e) => { note(&e) },"` must go red.
  4. In `visit_stmt`, replace `is_wild(&l.pat)` with `true` → `"Err(e) => { let r = describe(&e); r },"` must go red.
  5. In `format_arg_escapes`, delete the new `is_shared_borrow_of_name` `continue` → `println!("{}", &e)` row must go red.
  Any survivor is a defect in the rows: fix the row, not the mutant.

- [ ] **Step 7: The AFTER census on the clone**

Run the Task-0 Step-4 command again. Expected: `arm sites: 225` (unchanged — the classification moves, sites do not), `arms handled` ≤ 65, `arms escaped` ≥ 121, `arms handled + arms escaped + arms propagate == 225`. Ledger block **census AFTER** with the four numbers and the delta (`65 − handled_after`).

- [ ] **Step 8: Commit**

```bash
cd /home/brice/workspace/sensorium && git add rust/sensorium-transform/src/escape.rs rust/sensorium-transform/src/arms.rs && \
git commit -m "feat(transform)!: a &e borrow is exempt only where the borrowing call's product is dropped (design B1)

The old exemption proved the BORROW could not outlive the arm and said
nothing about the call's VALUE, so \`let (s, v) = map_error(&e, ..)\` read
arm_handled. Now: exempt as a direct argument of a call that is a \`;\`
statement, a \`let _ =\`, or a logging macro's argument; everywhere else the
borrow escapes (arm_ambiguous). Clone census: handled 65 -> <N2>, escaped
121 -> <N4>, sites 225 unchanged.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn" && git show --stat HEAD | head -8
```

---

### Task 2: Converter — the exit hop prefers text (design B3, §3)

**Files:**
- Modify: `rust/cargo-sensorium/src/convert/chains/mod.rs:27-32` (module doc), `:359-414` (`close_frame`)
- Test: `rust/cargo-sensorium/src/convert/chains/tests.rs` (+1), `rust/cargo-sensorium/tests/convert_errflow_chains.rs` (+1)

**Interfaces:**
- Consumes: `Machine { chains: Vec<Chain>, stack }`, `Chain { holder, merged, sink, last: ErrText, .. }`, `ErrText::matches`, `hop_out`, `open_at_exit`; test helpers `call`, `ret_err`, `ret`, `mint`, `serials`, `last_of` (`tests.rs:6-77`); `Fixture`, `wire::SpoolBuilder`, `site`, `err_site`, `chain_events` (`convert_errflow_chains.rs:1-32`, `tests/common/`).
- Produces: no interface change; `ChainEvent` unchanged.

- [ ] **Step 1: Write the failing unit test** — append to `rust/cargo-sensorium/src/convert/chains/tests.rs`:

```rust
/// The keep-first-error shape (design §3, CARRIED-DEBT 2026-09-05): A holds
/// TWO chains -- B1 from `first`, then C1 from `second` on top -- and returns
/// B1. The exit hop belongs to the chain whose text the RETURN carries, not to
/// the innermost; before the borrow-repair slice it went to C1 labelled
/// `translated`, and B1 was left without its hop.
#[test]
fn an_err_close_hops_the_held_chain_whose_text_it_carries_not_the_innermost() {
    let events = mint(
        &[
            call(0),                                // A
            call(1),                                // first
            ret_err(2, "demo::E", "B1"),            // chain B1, holder A
            call(3),                                // second
            ret_err(4, "demo::E", "C1"),            // chain C1, holder A, innermost
            ret_err(5, "demo::E", "B1"),            // A returns the FIRST error
        ],
        false,
    );
    let s = serials(&events);
    assert_eq!(s.len(), 2, "two chains, no merge: {events:#?}");
    let (b1, c1) = (events[0].serial, events[1].serial);
    let exit = events
        .iter()
        .find(|e| e.seq == 5)
        .unwrap_or_else(|| panic!("no event at A's close: {events:#?}"));
    assert_eq!(exit.serial, b1, "the hop is B1's, whose text the RETURN carries");
    assert!(!exit.translated, "same text, so not a translation: {exit:#?}");
    assert_eq!(exit.hop, 2);
    assert!(
        !events.iter().any(|e| e.seq == 5 && e.serial == c1),
        "C1 took no exit hop: {events:#?}"
    );
    for serial in [b1, c1] {
        assert_ne!(last_of(&events, serial).terminal, Some(Terminal::Merged));
    }
}
```

- [ ] **Step 2: Run it red**

Run: `cd /home/brice/workspace/sensorium/rust && CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target cargo test -p cargo-sensorium --lib an_err_close_hops_the_held_chain 2>&1 | grep -E "^test |panicked|assertion"`
Expected: FAIL at "the hop is B1's" (today the hop carries C1's serial, `translated: true`).

- [ ] **Step 3: Implement** — in `close_frame`, after `let parent = …;` and before the walk:

```rust
        // The chain the RETURN is ABOUT is the held one whose text it carries
        // (design B3, 2026-09-05): the same `held_matching` rule the RAISE and
        // HANDLED rows use, restricted to chains that can still take a hop.
        // Innermost is the fallback, which is also the answer for a RETURN
        // whose text is a wildcard (cut or unread) -- it matches every chain.
        let preferred = self.chains.iter().rposition(|c| {
            c.holder == Some(frame.id) && !c.merged && !c.sink && text.matches(&c.last)
        });
```

and change the hop condition to

```rust
                    if outcome == Outcome::Err
                        && !consumed_err
                        && preferred.is_none_or(|p| p == i)
                    {
```

Update the module doc at lines 27–32 (the CLOSE row now prefers the matching text, innermost as the fallback) and `close_frame`'s doc comment; cite design B3 and the date.

- [ ] **Step 4: Run green; the whole crate**

Run: `cd /home/brice/workspace/sensorium/rust && CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target cargo test -p cargo-sensorium 2>&1 | grep -E "^test result|FAILED|panicked"`
Expected: all `ok` (the existing chain tests pin the single-chain and wildcard behaviours and must not move).

- [ ] **Step 5: Write the failing e2e test** — append to `rust/cargo-sensorium/tests/convert_errflow_chains.rs`, modelled on `a_sink_absorbs_the_held_chain_it_names_over_the_nested_one` (same header, same builder calls; only the records differ):

```rust
/// Design B3 (2026-09-05): a frame closing `err` while holding two chains
/// hands the exit hop to the chain whose text the RETURN carries.
#[test]
fn an_err_close_holding_two_chains_hops_the_one_whose_text_it_returns() {
    let f = Fixture::new("errflow-chains-keep-first-error");
    f.manifest(&[
        site(0, "outer", 3, "value"),
        site(1, "first", 10, "value"),
        site(2, "second", 20, "value"),
    ]);
    wire::write_proc_header_caps(
        &f.spool_dir,
        626,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
        Some(true),
    );
    wire::SpoolBuilder::new(626, 1, "main")
        .version(3)
        .call(0, 1000, 0, 0)
        .call(1, 1100, 0, 1)
        .ret_err_typed(2, 1200, 0, 1, Some("demo::E"), Some("Err(B1)"))
        .call(3, 1300, 0, 2)
        .ret_err_typed(4, 1400, 0, 2, Some("demo::E"), Some("Err(C1)"))
        // `outer` returns the FIRST error while holding both chains.
        .ret_err_typed(5, 1500, 0, 0, Some("demo::E"), Some("Err(B1)"))
        .thread_end(6, 1600)
        .write(&f.spool_dir);
    let rows = chain_events(&f.converted());

    let b1 = rows[0]["chain"]["serial"].clone();
    let exits: Vec<_> = rows
        .iter()
        .filter(|r| r["chain"]["hop"] == serde_json::json!(2))
        .collect();
    assert_eq!(exits.len(), 1, "one exit hop: {rows:#?}");
    assert_eq!(exits[0]["chain"]["serial"], b1, "the hop is the first error's: {rows:#?}");
    assert_eq!(exits[0]["chain"]["translated"], serde_json::json!(false));
}
```

(If `write_proc_header_caps`'s pid must be unique per fixture in this file, use the next unused value; read the neighbours.)

- [ ] **Step 6: Run the e2e test red-then-green** — it is red only against the pre-Step-3 binary; run it now and confirm green:

Run: `cd /home/brice/workspace/sensorium/rust && CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target cargo test -p cargo-sensorium --test convert_errflow_chains 2>&1 | grep -E "^test |test result"`
Expected: all `ok`, including the new one.

- [ ] **Step 7: Mutation-test** — replace `preferred.is_none_or(|p| p == i)` with `true` (today's rule) → BOTH new tests must go red (unit: "the hop is B1's"; e2e: serial mismatch). Restore. Second mutant: drop `&& !c.sink` from `preferred` → run the whole crate; `a_sink_then_an_err_close_ends_that_chain_as_handled_then_failed` and the new test must stay green (an equivalent mutant on the corpus? no: a sunk chain is removed before the hop decision — if nothing goes red, ADD a unit test where the matching chain is `sink` and the innermost non-matching chain takes the fallback hop, and record it).

- [ ] **Step 8: clippy + fmt, commit**

```bash
cd /home/brice/workspace/sensorium/rust && CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target cargo clippy -p cargo-sensorium --all-targets -- -D warnings 2>&1 | tail -1 && cargo fmt --check && cd .. && \
git add rust/cargo-sensorium/src/convert/chains/mod.rs rust/cargo-sensorium/src/convert/chains/tests.rs rust/cargo-sensorium/tests/convert_errflow_chains.rs && \
git commit -m "fix(convert): an err close hops the held chain whose text the RETURN carries, innermost as the fallback (design B3)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn" && git show --stat HEAD | head -8
```

---

### Task 3: Corpus — `err_borrowed_into_value` and `keep_first_error`

**Files:**
- Create: `corpus/rust/err_borrowed_into_value/Cargo.toml`, `src/main.rs`, `questions.yaml`
- Create: `corpus/rust/keep_first_error/Cargo.toml`, `src/main.rs`, `questions.yaml`
- Modify: `corpus/rust/README.md` (two rows in the rung-3 table; the counts in its first sentence and the "Fifteen cases" heading sentence)
- Test: `corpus/run_corpus.py --only rust/<case>` with the debug driver; `tests/test_corpus.py`

**Interfaces:**
- Consumes: the debug driver `/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium` built from THIS branch after T1+T2 (`cargo build -p cargo-sensorium`); `corpus/run_corpus.py`'s `questions.yaml` grammar (`program: cargo`, `cargo_args: ["run"]`, `command`, `expect_exit`, `expect_contains`, `expect_line` groups, `expect_absent`).
- Produces: two cases E6-again′ counts (20 `exceptions` questions in all).

- [ ] **Step 1: Build the driver from this branch**

Run: `cd /home/brice/workspace/sensorium/rust && CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target cargo build -p cargo-sensorium 2>&1 | tail -1`
Expected: `Finished`.

- [ ] **Step 2: Write `corpus/rust/err_borrowed_into_value`**

`Cargo.toml`:
```toml
[package]
name = "corpus_err_borrowed_into_value"
version = "0.1.0"
edition = "2021"
publish = false

[[bin]]
name = "err_borrowed_into_value"
path = "src/main.rs"
```

`src/main.rs` — exactly this (line numbers are pinned by the questions):
```rust
//! The fourth side of the line `err_stored`, `logged_arm` and
//! `err_rendered_into_value` draw: an `Err(e) =>` arm that hands a SHARED
//! BORROW of the error to a helper and keeps what the helper built.
//!
//! `logged_arm` borrows the error to print it and drops it -- a swallow.
//! `err_rendered_into_value` renders it with `format!` and returns the
//! rendering. Here the arm does the same thing one function call out:
//! `describe(&e)` takes only a borrow, so the arm still owns the error, but
//! the `(code, body)` it returns is a rendering of the failure and that pair
//! is the value `respond` hands to every caller. Before the 2026-09-05
//! borrow repair the escape test exempted `&e` wherever it appeared and this
//! arm read HANDLED -- a SWALLOWED verdict on a failure the caller received
//! as a 503. On the bloomery clone the shape is `api_v1.rs:396` and `:515`.
//!
//! Seeded bug: the reply says `503 store unavailable: cannot open store.db`
//! and nothing on the terminal says which call produced it; the failure DID
//! reach the caller, inside the reply, which is exactly why the tool must
//! read this arm as ambiguous and not as a swallow.

#[derive(Debug)]
struct Unavailable(String);

#[derive(Debug)]
struct Reply {
    code: u16,
    body: String,
}

/// The store is missing, so this always fails.
fn open(path: &str) -> Result<u32, Unavailable> {
    Err(Unavailable(path.to_owned()))
}

/// Maps a borrowed error to a status and a body: the helper `map_error` on
/// the clone. Its PRODUCT is what leaves the arm.
fn describe(e: &Unavailable) -> (u16, String) {
    (503, format!("store unavailable: cannot open {}", e.0))
}

/// The arm under test: `&e` is a borrow, and the pair the call returns is
/// the reply every caller gets.
fn respond(path: &str) -> Reply {
    match open(path) {
        Ok(n) => Reply { code: 200, body: format!("rows: {n}") },
        Err(e) => {
            let (code, body) = describe(&e);
            Reply { code, body }
        }
    }
}

fn main() {
    let reply = respond("store.db");
    println!("{} {}", reply.code, reply.body);
}
```
(`open` is at line 30, the `Err(e) =>` arm at line 45, `respond` at line 42.)

`questions.yaml`:
```yaml
program: cargo
cargo_args: ["run"]
questions:
  - id: was-the-open-failure-swallowed
    ask: >
      The process printed `503 store unavailable: cannot open store.db` and
      exited 0. Was the failure to open the store dropped somewhere?
    truth: >
      No, and the tool must not say it was. `open` returned
      `Err(Unavailable("store.db"))`, the `Err(e) =>` arm in `respond`
      handed a BORROW of it to `describe`, and `describe`'s product -- a
      status and a body that render the failure -- is the `Reply` every
      caller gets. The borrow proves the arm still owns the error; it says
      nothing about the value the call returned, and that value carried the
      failure out. This is `err_rendered_into_value` one function call out,
      and the shape endpoint E6⁗ measured on the bloomery clone
      (`api_v1.rs:396`, `:515`). The arm reads ambiguous; the tally carries
      no swallow.
    why_logs_fail: >
      The terminal shows the 503 and nothing else: which call failed, and
      that the arm in `respond` is where a status was chosen for it, is not
      on the terminal. A tool that read this arm as a swallow -- the reading
      before the 2026-09-05 borrow repair -- would send a reader hunting for
      a dropped error that was in the reply all along. Nothing panics, so
      RUST_BACKTRACE never fires.
    command: ["exceptions", "$RUN"]
    expect_exit: 0
    expect_contains: ["dispositions: ambiguous 1"]
    expect_line:
      - ["an Err(..) arm at", "respond L45",
         "bound it to a name and let the name escape"]
      - ["hops:", "open L30 exit", "respond L45 arm_ambiguous"]
    expect_absent: ["SWALLOWED", "dispositions: swallowed", "panicked",
                    "returned to the harness"]
  - id: what-did-respond-hand-back
    ask: >
      `open` failed and `respond` returned normally. What did `respond`
      hand back?
    truth: >
      A `Reply { code: 503, body: "store unavailable: cannot open store.db" }`
      -- the failure travelled out of the frame inside the return value, by
      way of `describe`, which took the error by reference and returned the
      rendering. One frame down, `open` returned `Err(Unavailable("store.db"))`.
    why_logs_fail: >
      The printed line is the reply's own text; that it was built from an
      `Err` two frames down, by a helper that only borrowed it, is nowhere on
      the terminal.
    command: ["tree", "$RUN"]
    expect_exit: 0
    expect_line:
      - ["respond(", "-> Reply { code: 503, body: \"store unavailable: cannot open store.db\" }"]
      - ["open(", "-> Err(Unavailable(\"store.db\"))"]
      - ["describe(", "-> (503, \"store unavailable: cannot open store.db\")"]
    expect_absent: ["!! ", "(open)"]
```

- [ ] **Step 3: Run the case, pin what the run prints**

Run: `cd /home/brice/workspace/sensorium && SENSORIUM_CARGO_SENSORIUM=/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/corpus-target .venv/bin/python corpus/run_corpus.py --only rust/err_borrowed_into_value`
Expected: both questions pass. If a needle misses on wording that is TRUE (a frame id, an argument rendering), correct the needle to what the tool prints and say so in the report; if the run prints a SWALLOWED line, T1 is wrong — stop and report.

- [ ] **Step 4: Mutate the case** — change the arm to `Err(e) => { report(&e); Reply { code: 503, body: String::new() } }` with `fn report(e: &Unavailable) { eprintln!("{e:?}"); }` → run → the first question must go red with `swallowed 1` in the output (the shape is now `logged_arm`'s through a helper: a true swallow, which is the reading B1 keeps). Restore.

- [ ] **Step 5: Write `corpus/rust/keep_first_error`**

`Cargo.toml`:
```toml
[package]
name = "corpus_keep_first_error"
version = "0.1.0"
edition = "2021"
publish = false

[[bin]]
name = "keep_first_error"
path = "src/main.rs"
```

`src/main.rs` — exactly this:
```rust
//! A frame that holds TWO different errors and returns the FIRST.
//!
//! `pick` calls `first` (fails with `Refused(1)`), then `second` (fails with
//! `Refused(2)`), and returns the first error it saw -- the keep-first-error
//! shape. The chain machine used to hand the exit hop to the INNERMOST held
//! chain (the second error's), labelling it `translated` because the text
//! changed, and left the first error's chain without its hop. Since the
//! 2026-09-05 borrow-repair slice the hop goes to the chain whose text the
//! RETURN carries.
//!
//! Seeded bug: `main` logs the failure and carries on, so the process exits 0
//! with `ok: 0` and the refusal is on stderr only -- a swallow of the FIRST
//! error, which is the one the caller was handed. The second error never left
//! `pick`: its chain reads ambiguous, never swallowed, and never `translated`.

#[derive(Debug)]
struct Refused(u32);

fn first() -> Result<u32, Refused> {
    Err(Refused(1))
}

fn second() -> Result<u32, Refused> {
    Err(Refused(2))
}

/// Holds both errors, returns the first: the keep-first-error shape.
fn pick() -> Result<u32, Refused> {
    let a = first();
    let b = second();
    if a.is_err() {
        return a;
    }
    b
}

fn main() {
    let value = match pick() {
        Ok(v) => v,
        // BUG: printed, then forgotten -- the first refusal is swallowed here.
        Err(e) => {
            eprintln!("pick failed: {e:?}");
            0
        }
    };
    println!("ok: {value}");
}
```
(`first` at line 19, `second` at 23, `pick` at 28, the `Err(e) =>` arm in `main` at line 41.)

`questions.yaml`:
```yaml
program: cargo
cargo_args: ["run"]
questions:
  - id: which-error-was-swallowed-and-which-way-did-it-travel
    ask: >
      stderr says `pick failed: Refused(1)` and the process exited 0 with
      `ok: 0`. Which failure was dropped, and where did it come from?
    truth: >
      The FIRST one. `first` returned `Err(Refused(1))`; `pick` held it,
      called `second` (which failed with `Refused(2)`), and returned the first
      error; `main`'s `Err(e) =>` arm printed it and carried on -- a swallow
      of `Refused(1)` at that arm. The hops name `first`, then `pick`'s exit,
      then the arm, with no `translated` on the way: the exit hop belongs to
      the chain whose text `pick` returned. `Refused(2)` never left `pick`
      and reads ambiguous, not swallowed. Before the 2026-09-05 borrow
      repair the machine gave `pick`'s exit hop to the INNERMOST chain --
      `Refused(2)`'s -- labelled `translated`, and the swallow would have
      been reported as the second error's chain.
    why_logs_fail: >
      stderr shows one refusal and stdout shows a success. That the printed
      refusal was the first of two, and that the second was discarded inside
      `pick` without a word, is not on the terminal; RUST_BACKTRACE never
      fires because nothing panics.
    command: ["exceptions", "$RUN"]
    expect_exit: 0
    expect_contains: ["dispositions: swallowed 1, ambiguous 1"]
    expect_line:
      - ["SWALLOWED", "arm_handled", "main L41", "returned ok"]
      - ["hops:", "first L19 exit", "pick L28 exit", "main L41 arm_handled"]
      - ["Refused(2)"]
    expect_absent: ["translated", "dispositions: swallowed 2", "panicked",
                    "returned to the harness"]
  - id: what-did-pick-return
    ask: >
      Both helpers failed. Which error did `pick` return?
    truth: >
      `Err(Refused(1))` -- the first. `second` also returned
      `Err(Refused(2))`, and `pick` dropped it on the floor.
    why_logs_fail: >
      Only the first refusal is printed, by `main`; the second is never
      printed anywhere.
    command: ["tree", "$RUN"]
    expect_exit: 0
    expect_line:
      - ["pick(", "-> Err(Refused(1))"]
      - ["first(", "-> Err(Refused(1))"]
      - ["second(", "-> Err(Refused(2))"]
    expect_absent: ["!! ", "(open)"]
```

- [ ] **Step 6: Run the case; pin the ambiguous sentence**

Run the Step-3 command with `--only rust/keep_first_error`. Expected: both pass. The line the tool prints for `Refused(2)`'s chain (the ambiguous one) is pinned as an additional `expect_line` group AFTER reading it — copy the sentence, check it is TRUE of the program (it never left `pick`), and add it; record the sentence in the report.

- [ ] **Step 7: Mutate the machine** — in the workspace, temporarily replace `preferred.is_none_or(|p| p == i)` with `true` (T2's mutant), rebuild the debug driver, re-run the case → the first question must go red (the hops group names `second L23`, `translated` appears). Restore the source, rebuild, re-run green. **Rebuild into a fresh scratch target for the mutant** (`CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/tmp/mutant-target`) so the corpus target never serves a stale mutant binary (E6‴'s ops lesson).

- [ ] **Step 8: README rows + counts, the corpus test, commit**

In `corpus/rust/README.md`: first sentence `Twenty-nine cases` → `Thirty-one cases`; the rung-3 section's `Fifteen cases added` → `Seventeen cases added`; two rows in the rung-3 table:

```
| `err_borrowed_into_value` | an `Err(e) =>` arm that hands `&e` to a helper and keeps the helper's product -- the failure travelled to the caller inside the reply, so the arm reads ambiguous and NEVER a swallow (the shape E6⁗ measured on bloomery's `api_v1.rs`) | `exceptions`, `tree` |
| `keep_first_error` | a frame holding two different errors that returns the FIRST: the exit hop follows the returned text (no `translated`), the first error is swallowed by `main`'s log-and-continue arm, the second reads ambiguous | `exceptions`, `tree` |
```

Run: `cd /home/brice/workspace/sensorium && SENSORIUM_CARGO_SENSORIUM=/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/corpus-target PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_corpus.py -q 2>&1 | tail -2 && .venv/bin/python corpus/run_corpus.py 2>&1 | tail -3`
Expected: `test_corpus` green; the corpus summary reports 51 cases (49 + 2), 108 questions, 0 failures (the Python cases run without the driver variable too).

```bash
cd /home/brice/workspace/sensorium && git add corpus/rust/err_borrowed_into_value corpus/rust/keep_first_error corpus/rust/README.md && \
git commit -m "test(corpus): err_borrowed_into_value (a &e handed to a helper whose product is kept reads ambiguous) and keep_first_error (the exit hop follows the returned text)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn" && git show --stat HEAD | head -12
```

---

### Task 4: Acceptance tooling, box-free tests, then §1 locked ALONE

**Files:**
- Modify: `rust/tests/acceptance_phases_rung3.py:330-339` (`phase_e6prime(paths, cfg, tail=("--lib",))`)
- Create: `rust/tests/acceptance_e6q.py`, `rust/tests/acceptance_schema_e6q.py`, `rust/tests/render_e6q.py`
- Create: `tests/test_acceptance_e6q.py`
- Create: `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md` (header + §1 only; committed ALONE)

**Interfaces:**
- Consumes (imported, never copied): from `acceptance_e6ppp` — `logs_at`, `arm_paths`, `build_driver`, `phase_prep_build`, `arm_rows`, `executed_arms`, `sweep_other_runs`, `mark_load`, `LOADS`; from `acceptance_rung3` — `byte_lock_check`, `rung3_config`, `preflight`, `cleanup`, `install_load_hook`; from `acceptance_phases_rung3` — `phase_e6prime`, `phase_e6`, `phase_e7pp`, `phase_e0pp`, `SWALLOWED`, `TALLY`, `SWALLOW_LINE`, `_sink_files`; from `acceptance_lib` — `env_paths`, `driver_cmd`, `run`, `plain_env`, `sha256_file`, `Refused`, `step`, `free_gb`.
- Produces: `acceptance_e6q.main()` → `<ledger>/acceptance-e6q/results-e6q-raw.json`, `e6q.DONE|.FAILED`; `assemble_e6q(raw) -> dict` → `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.results.json`; `render_e6q.py` → §3 markdown; env: `SENSORIUM_BASE_DRIVER`, `SENSORIUM_BASE_WORKTREE`, `SENSORIUM_CONTROL_TARGET` (new), plus the E6‴ set.

- [ ] **Step 1: `phase_e6prime` gains the selector tail** — in `rust/tests/acceptance_phases_rung3.py`:

```python
def phase_e6prime(paths, cfg, tail: tuple[str, ...] = ("--lib",)) -> dict:
    ...
    step(f"E6': one instrumented {' '.join((*cfg['pkg'], *tail))} run of the clone")
    res = run(driver_cmd(paths, *cfg["pkg"], *tail),
              ...
```
Only those two lines change. Run: `cd /home/brice/workspace/sensorium && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_acceptance_e6ppp.py tests/test_acceptance_rung3.py -q 2>&1 | tail -2` → Expected: green (the default keeps every existing caller byte-for-byte; `test_the_two_arms_differ_only_in_the_package_selector` still passes).

- [ ] **Step 2: Write the failing box-free tests** — `tests/test_acceptance_e6q.py`, modelled on `tests/test_acceptance_e6ppp.py` (same `_paths(tmp_path)` helper and skip-by-name lock helper):

```python
def test_the_two_head_arms_differ_only_in_the_selector_and_the_lib_tail(tmp_path):
    p = _paths(tmp_path)
    a = driver_cmd(p, *runner.ARM_A["selector"], *runner.ARM_A["tail"])
    ws = driver_cmd(p, *runner.ARM_WS["selector"], *runner.ARM_WS["tail"])
    assert a[-3:] == ["-p", "bloomery-daemon", "--lib"]
    assert ws[-1:] == ["--workspace"] and "--lib" not in ws
    assert a[:-3] == ws[:-1]

def test_the_control_arm_is_the_ws_arm_under_the_base_driver_in_its_own_target_and_store(tmp_path):
    p = _paths(tmp_path)
    ws = runner.arm_paths_for(p, runner.ARM_WS)
    ws0 = runner.arm_paths_for(p, runner.ARM_WS0)
    assert runner.ARM_WS0["selector"] == runner.ARM_WS["selector"]
    assert runner.ARM_WS0["tail"] == runner.ARM_WS["tail"]
    assert ws0["sensorium_driver"] == p["sensorium_base_driver"] != ws["sensorium_driver"]
    assert ws0["sensorium_acceptance_target"] == p["sensorium_control_target"] != ws["sensorium_acceptance_target"]
    assert ws0["sensorium_dir"] != ws["sensorium_dir"]

def test_flip_diff_counts_handled_to_ambiguous_and_names_every_other_transition():
    before = {"rows": [row("a.rs", 1, "arm_handled"), row("a.rs", 2, "arm_handled"),
                       row("b.rs", 3, "arm_propagate"), row("c.rs", 9, "arm_handled")]}
    after = {"rows": [row("a.rs", 1, "arm_ambiguous"), row("a.rs", 2, "arm_handled"),
                      row("b.rs", 3, "arm_propagate"), row("c.rs", 9, "arm_propagate"),
                      row("d.rs", 4, "arm_ambiguous")]}
    d = runner.flip_diff(before, after)
    assert d["changed_count"] == 2
    assert d["transitions"] == {"arm_handled->arm_ambiguous": 1, "arm_handled->arm_propagate": 1}
    assert d["only_handled_to_ambiguous"] is False
    assert d["only_before"] == [] and d["only_after"] == [{"file": "d.rs", "line": 4, "how": "arm_ambiguous"}]

def test_flip_diff_reports_the_two_api_v1_rows_by_name():
    before = {"rows": [row("crates/bloomery-daemon/src/api_v1.rs", 396, "arm_handled"),
                       row("crates/bloomery-daemon/src/api_v1.rs", 515, "arm_handled")]}
    after = {"rows": [row("crates/bloomery-daemon/src/api_v1.rs", 396, "arm_ambiguous"),
                      row("crates/bloomery-daemon/src/api_v1.rs", 515, "arm_ambiguous")]}
    d = runner.flip_diff(before, after)
    assert d["named"]["crates/bloomery-daemon/src/api_v1.rs:396"] == {"before": "arm_handled", "after": "arm_ambiguous", "flipped": True}
    assert d["named_all_flipped"] is True

def test_a_named_row_missing_from_a_build_is_reported_not_assumed_flipped():
    d = runner.flip_diff({"rows": []}, {"rows": []})
    assert d["named"]["crates/bloomery-daemon/src/api_v1.rs:515"]["flipped"] is None
    assert d["named_all_flipped"] is False

def test_control_lines_at_flipped_sites_is_computed_only_over_the_flip_set():
    flip = {"changed": [{"file": "crates/x/src/a.rs", "line": 5}]}
    parsed = [{"sink": "/clone/crates/x/src/a.rs:5"}, {"sink": "/clone/crates/x/src/a.rs:7"}, {"sink": None}]
    out = runner.lines_at_flipped_sites(parsed, flip, "/clone")
    assert out["count"] == 1 and out["unresolved"] == 1

def test_neither_ws_arms_false_accusation_count_is_ever_invented():
    doc = assemble_e6q({"raw_arm_a": {"swallowed_count": 3, "union_swallowed_count": 3}, "raw_arm_ws": {"swallowed_count": 1, "union_swallowed_count": 9}, "raw_arm_ws0": {"swallowed_count": 2, "union_swallowed_count": 11}})
    for k in ("E6qA", "E6qWS", "E6qWS0"):
        assert doc["endpoints"][k]["headline"]["value"] is None
        assert doc["endpoints"][k]["headline"]["dropped"]

def test_the_control_verdict_is_not_measured_until_the_hand_adjudication_is_pasted():
    doc = assemble_e6q({"raw_arm_ws0": {"swallowed_count": 0, "union_swallowed_count": 0}})
    assert doc["endpoints"]["E6qWS0"]["discriminating"]["value"] is None

def test_the_flip_gate_cells_carry_the_frozen_delta_and_the_measured_count():
    doc = assemble_e6q({"raw_flip": {"changed_count": 7, "only_handled_to_ambiguous": True, "named_all_flipped": True}, "frozen_census": {"arms_handled_before": 65, "arms_handled_after": 58}})
    assert doc["endpoints"]["Eflip"]["changed_equals_delta"]["value"] is True
    assert doc["endpoints"]["Eflip"]["changed_equals_delta"]["n"] == 7
```

plus the lock tests copied from `test_acceptance_e6ppp.py` with `runner.DOC`/`runner.BYTE_LOCK` (they skip by name until Step 6 sets the sha) and the renderer's "not measured" test. `row(file, line, how)` is a local helper building `arm_rows`' row shape (`{"file","line","qualname","hows":[how],"units":1}`).

- [ ] **Step 3: Run them red**

Run: `cd /home/brice/workspace/sensorium && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_acceptance_e6q.py -q 2>&1 | tail -3`
Expected: ImportError (`acceptance_e6q` does not exist).

- [ ] **Step 4: Write the runner, schema and renderer**

`rust/tests/acceptance_e6q.py` — the shape of `acceptance_e6ppp.py`, with these definitions (the rest is reuse):

```python
PLAN = REPO / ".superpowers" / "sdd" / "2026-09-05-sensorium-rung3-borrow-repair"
LEDGER = PLAN
BASE = PLAN / "acceptance-e6q"
LOGS = BASE / "logs"
DOC = REPO / "docs" / "superpowers" / "acceptance" / "2026-09-05-sensorium-rung3-e6q.md"
BYTE_LOCK = None          # Step 6 sets the sha of the commit that locked §1
BASE_COMMIT = "d1b1b57"   # the pre-repair main the control driver is built from

ARM_A   = {"label": "a",   "selector": ["-p", "bloomery-daemon"], "tail": ["--lib"], "driver": "head"}
ARM_WS  = {"label": "ws",  "selector": ["--workspace"],            "tail": [],        "driver": "head"}
ARM_WS0 = {"label": "ws0", "selector": ["--workspace"],            "tail": [],        "driver": "base"}
NAMED_ROWS = ["crates/bloomery-daemon/src/api_v1.rs:396", "crates/bloomery-daemon/src/api_v1.rs:515"]
FROZEN_CENSUS = {...}     # from the ledger: before/after handled, escaped, arm_sites, source "§1"
```

Re-point every shared module's log pointer AFTER the imports (`lib.LEDGER = LEDGER; lib.LOGS = LOGS; ph.LOGS = LOGS; e6ppp.LOGS = LOGS; e6ppp.BASE = BASE`) — `acceptance_rung3` AND `acceptance_e6ppp` both re-point them in their module bodies (the E6‴ record §2's lesson).

`env_paths_e6q()` = `lib.env_paths(False)` plus three required variables: `SENSORIUM_BASE_DRIVER` → `paths["sensorium_base_driver"]`, `SENSORIUM_BASE_WORKTREE` → `paths["sensorium_base_worktree"]`, `SENSORIUM_CONTROL_TARGET` → `paths["sensorium_control_target"]`; missing ones refused together.

`verify_base_driver(paths) -> dict`: `git -C <worktree> rev-parse HEAD` must start with `BASE_COMMIT` and the worktree's porcelain must be empty, else `Refused`; records the driver's sha256 and mtime and `<driver> --version`'s text (must contain `cargo-sensorium 0.3.0`).

`arm_paths_for(paths, arm) -> dict`: `e6ppp.arm_paths(paths, arm["label"])`, and for `arm["driver"] == "base"` also `p["sensorium_driver"] = paths["sensorium_base_driver"]` and `p["sensorium_acceptance_target"] = paths["sensorium_control_target"]`.

`phase_arm(paths, cfg, arm) -> dict`: as `e6ppp.phase_arm` but calling `r3.phase_e6prime(ap, acfg, tail=tuple(arm["tail"]))`, then `e6ppp.sweep_other_runs`, then `e6ppp.executed_arms`; records `arm["driver"]`, the driver path and sha used.

`flip_diff(before: dict, after: dict) -> dict`: key rows by `(file, line)`; `how` of a row = its single `hows[0]` (a row with more than one `how` is reported under `multi_how` and excluded from transitions); returns `{"changed": [{file, line, qualname, before, after}], "changed_count", "transitions": {"<b>-><a>": n}, "only_handled_to_ambiguous": bool, "only_before": [...], "only_after": [...], "named": {name: {"before", "after", "flipped": True|False|None}}, "named_all_flipped": bool, "multi_how": [...]}`.

`lines_at_flipped_sites(parsed: list, flip: dict, clone_root: str) -> dict`: for every parsed SWALLOWED line whose `sink` (a `"<abs file>:<line>"` string) resolves under `clone_root` to a `(file, line)` in `flip["changed"]`, count it; `{"count", "lines": [...], "unresolved": n}` — the computed EVIDENCE for the WS0 hand adjudication, never its verdict.

`main()` order: byte-lock → `env_paths_e6q` → config (`rung3.rung3_config` + `e6_workdir`, `frozen_census`, the arms) → `verify_base_driver` → `e6ppp.build_driver` (HEAD) → `rung3.preflight` → prep HEAD (`e6ppp.phase_prep_build(paths, cfg)`, acceptance target; `arms_after = out["arms"]`) → prep BASE (`e6ppp.phase_prep_build(arm_paths_for(paths, ARM_WS0), cfg)`, control target; `arms_before`) → `raw_flip = flip_diff(arms_before, arms_after)` → `raw_arm_a` → `raw_arm_ws` → `raw_arm_ws0` → `raw_flip_lines = {arm: lines_at_flipped_sites(...)}` for ws and ws0 → E6-again (`r3.phase_e6`, corpus target from `SENSORIUM_CORPUS_TARGET`) → E7⁗ (`r3.phase_e7pp`) → E0‴ (`r3.phase_e0pp(arm_paths_for(paths, ARM_WS), cfg, <the ws process with the most events>)`) → `rung3.cleanup` → write `results-e6q-raw.json` → `assemble_only` → `e6q.DONE`/`.FAILED` with `exit=<n>`. Every phase inside its own `logs_at(LOGS / "<phase>")`.

`rust/tests/acceptance_schema_e6q.py::assemble_e6q(raw) -> dict`: endpoints `E6qA`, `E6qWS`, `E6qWS0` via a copy of `acceptance_schema_e6ppp._arm`'s SHAPE (import `meas`, `_drop`, `_sweep_added`, `GUARDED_*` from it; the lens string names the selector and tail and, for WS0, the base driver); `E6qWS0` additionally carries `lines_at_flipped_sites` (computed) and `discriminating: meas(None, …, "decided by the hand adjudication of §4: ≥ 1 FALSE accusation at a flip-set arm", [BY_HAND])`; `Eflip` cells: `changed_count`, `only_handled_to_ambiguous`, `named_all_flipped`, `changed_equals_delta` (= `changed_count == frozen.arms_handled_before − frozen.arms_handled_after`, `n = changed_count`), `only_before_count`, `only_after_count`; `E6again` via `acceptance_schema_rung3`'s E6 assembler (import, do not copy); `E7q`, `E0ppp` from the rung-3 schema's shapes; `prep_head`, `prep_base`, `built_from`, `base_driver`, `loads`, `pins`. None-versus-zero: a phase that did not run is `None` with a reason.

`rust/tests/render_e6q.py`: renders §3 from the results json as `render_e6ppp.py` does (import its table helpers); prints `not measured (<reason>)` for a `None`.

- [ ] **Step 5: Run the box-free tests green; mutation-test them**

Run: `cd /home/brice/workspace/sensorium && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_acceptance_e6q.py tests/test_acceptance_e6ppp.py tests/test_acceptance_rung3.py -q 2>&1 | tail -3`
Expected: green (the lock tests skip BY NAME until Step 6). Mutations (Python: purge `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`): (1) `flip_diff` counts `arm_propagate->arm_ambiguous` as handled→ambiguous → transition test red; (2) `lines_at_flipped_sites` drops the clone-root strip → count test red; (3) `arm_paths_for` forgets the control target → control-arm test red; (4) `assemble_e6q` fills the WS0 headline with `union_swallowed_count` → invented-count test red; (5) `changed_equals_delta` compares against `arms_escaped` → flip-gate test red.

- [ ] **Step 6: Commit the tooling** (§1 is NOT in this commit):

```bash
cd /home/brice/workspace/sensorium && git add rust/tests/acceptance_phases_rung3.py rust/tests/acceptance_e6q.py rust/tests/acceptance_schema_e6q.py rust/tests/render_e6q.py tests/test_acceptance_e6q.py && \
git commit -m "test(acceptance): the E6⁗ runner — arms A/WS/WS0, the BEFORE/AFTER arm-manifest flip diff, E6-again′, E7⁗, E0‴; phase_e6prime takes a selector tail

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn" && git show --stat HEAD | head -10
```

- [ ] **Step 7: Write the acceptance document's header and §1, commit ALONE**

`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md`: a header in the shape of the E6‴ record's (what this document is, that E6‴ stands as written, the binding design = the borrow-repair design + rung-3 R15/R16, the driver lens, "**§1 is byte-locked**" paragraph naming the `awk` range), then `## 1. Pre-registration` = design §4's table VERBATIM with `<N1>`..`<N5>` replaced by the ledger's census numbers (BEFORE from T0: handled 65, escaped 121, sites 225; AFTER from T1), the lens paragraph, and "Reported without a gate". Then a line `## 2. Environment` followed by `(written by Task 5)` so the `awk` range closes. Nothing else.

```bash
cd /home/brice/workspace/sensorium && git add docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md && \
git commit -m "docs(rung3): pre-register E6⁗-A / E6⁗-WS / E6⁗-WS0 / E-flip / E6-again′ / E7⁗ / E0‴

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn" && git show --stat HEAD && git rev-parse --short HEAD
```
Record the sha in the ledger as **LOCK**.

- [ ] **Step 8: Point the runner at the lock; the lock tests run for real**

Set `BYTE_LOCK = "<sha>"` in `rust/tests/acceptance_e6q.py`; run `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_acceptance_e6q.py -q -k lock` → the real-document lock test passes and the one-byte-refusal test passes. Commit that one line: `chore(acceptance): E6⁗ runner locks §1 at <sha>`.

---

### Task 5: The measurement — once, detached, then the record

**Files:**
- Modify: `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md` (§2–§5)
- Create: `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.results.json` (by `--assemble`)
- Ledger: `<ledger>/acceptance-e6q/{launch.sh, e6q.pid, e6q.DONE, results-e6q-raw.json, logs/**}`

**Interfaces:**
- Consumes: T4's runner; the base driver from T0; env as below.

- [ ] **Step 1: Preflight (nothing measured yet)**

```bash
cd /home/brice/workspace/sensorium && git status --porcelain && git log --oneline -1 && \
git -C /mnt/extra/sensorium-rung2/bloomery rev-parse HEAD && git -C /mnt/extra/sensorium-rung2/bloomery status --porcelain && \
git -C /mnt/extra/sensorium-rung2/base-d1b1b57 rev-parse HEAD && sha256sum /mnt/extra/sensorium-rung2/rust-target-base/release/cargo-sensorium && \
rm -rf /mnt/extra/sensorium-rung2/corpus-target-e6q /mnt/extra/sensorium-rung2/sensorium-dir/e6q && mkdir -p /mnt/extra/sensorium-rung2/bloomery-target-control /mnt/extra/sensorium-rung2/sensorium-dir/e6q && \
df -h /mnt/extra | tail -1 && cat /proc/loadavg && pgrep -x cargo || echo no-cargo-running
```
Expected: porcelain empty (the untracked exit-status finding doc is Brice's and is fine); clone at `e209ed9`, clean; worktree at `d1b1b57`; the T0 sha; ≥ 40 GB free; load < 4; no cargo running.

- [ ] **Step 2: The launcher** — `<ledger>/acceptance-e6q/launch.sh`, modelled on E6‴'s `launch.sh`, adding:
```bash
export SENSORIUM_BASE_DRIVER=$B/rust-target-base/release/cargo-sensorium
export SENSORIUM_BASE_WORKTREE=$B/base-d1b1b57
export SENSORIUM_CONTROL_TARGET=$B/bloomery-target-control
export SENSORIUM_CORPUS_TARGET=$B/corpus-target-e6q
export SENSORIUM_DIR=$B/sensorium-dir/e6q
exec "$REPO/.venv/bin/python" rust/tests/acceptance_e6q.py
```
Launch: `cd /home/brice/workspace/sensorium && setsid nohup bash <ledger>/acceptance-e6q/launch.sh > <ledger>/acceptance-e6q/logs/e6q.log 2>&1 &` — then `ps -p $(cat <ledger>/acceptance-e6q/e6q.pid)` only. Read NOTHING under `logs/` until `e6q.DONE` or `e6q.FAILED` exists; poll with a Monitor/until-loop on the marker or the pid's death (both terminal states covered).

- [ ] **Step 3: On `.DONE`** — read `results-e6q-raw.json`; confirm `byte_lock.identical`, the base-driver verification, both prep builds `rc 0`, every arm `rc 0` or its cargo exit explained (a failing bloomery test is data, a driver refusal is infrastructure — say which), `traces_missing == []`. On `.FAILED` before any arm ran (a Refused): fix the infrastructure and relaunch from zero — that is an infrastructure kill, not a re-roll; on `.FAILED` after an arm produced numbers: STOP, record what was read, no relaunch without a ruling.

- [ ] **Step 4: Hand-adjudicate** — three tables (§4.1 A, §4.2 WS union, §4.3 WS0 union) in the E6‴ record's column shape (`# | Printed line | Sink file:line | log-and-continue? | Verdict (amended) | Reason from the source`), every SWALLOWED line, read fresh from the clone at `e209ed9`; §4.4 the counts under both readings with the guarded-arm column; §4.5 **the discrimination verdict**: the WS0 lines at flip-set arms (the computed `lines_at_flipped_sites` beside your reading of each), and which of `api_v1.rs:396`/`:515` executed in WS and WS0 (`executed_arms`); §4.6 E-flip: the changed rows named, transitions, the named rows, `changed_equals_delta`. Verdicts table: one row per §1 endpoint, the rule verbatim, the number, PASS/STOP — and for E6⁗-WS0 `DISCRIMINATING` / `NOT DISCRIMINATING`.

- [ ] **Step 5: §2 lens, §3 rendered, §5 gaps** — §2 from the raw json (both drivers, both targets, loads, disk, clone before/after, base worktree HEAD); §3 = `render_e6q.py` output pasted; §5: what was not measured, any deviation, the rows a reader may contest, the residuals found (recorded, never repaired post-lock).

- [ ] **Step 6: Assemble and commit**

```bash
cd /home/brice/workspace/sensorium && .venv/bin/python rust/tests/acceptance_e6q.py --assemble && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_acceptance_e6q.py -q 2>&1 | tail -1 && \
git add docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.results.json && \
git commit -m "docs(rung3): E6⁗ measured — <A verdict> / <WS verdict> / <WS0 discriminating?> / <E-flip> / <E6-again′> / <E7⁗> / <E0‴>

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn" && git show --stat HEAD | head -6
```
Then `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_acceptance_e6q.py -q -k lock` must still pass (the §1 range is untouched by §2–§5).

---

### Task 6: Docs, versions, CHANGELOG, CARRIED-DEBT, design pointers, PR body

**Files:**
- Modify: `rust/HONESTY.md` (§11's closing `&e` paragraph, lines 777–789), `rust/HONESTY-BLIND-SPOTS.md` (item 23), `rust/HONESTY-INDEX.md` (§11 rows citing E6⁗), `docs/TRACE-FORMAT.md` (§5 `translated` row), `docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md` (three dated pointers + R16 (vii)), `CHANGELOG.md`, `docs/CARRIED-DEBT.md`, `pyproject.toml`, `rust/sensorium-transform/Cargo.toml`, `rust/cargo-sensorium/Cargo.toml`, `rust/cargo-sensorium/src/driver.rs` (`DRIVER_VERSION` + 2 pins), `rust/cargo-sensorium/tests/driver_smoke.rs:125`, `rust/Cargo.lock`, `README.md` (the Rust-corpus sentence's count if it states one)
- Create: `<ledger>/pr-body-draft.md`

- [ ] **Step 1: Grep before writing a version**

Run: `cd /home/brice/workspace/sensorium && grep -rn "0\.3\.0\|0\.8\.0\|0\.3\.1\|0\.8\.1" --include=*.py --include=*.rs --include=*.toml --include=*.md . | grep -v "target/\|Cargo.lock\|\.venv\|CHANGELOG\|docs/superpowers\|format3\|fixtures\|async_focus\|test_diff\|stale_cache"`
Expected: exactly the pins the Global Constraints name (transform + cargo-sensorium Cargo.toml, `driver.rs` ×3 incl. `driver_smoke.rs`, `pyproject.toml`) plus `sensorium-rt`'s which stay. Anything else is a pin to move or to explain in the report.

- [ ] **Step 2: Versions** — `sensorium-transform` and `cargo-sensorium` `version = "0.3.1"`; `DRIVER_VERSION` → `"cargo-sensorium 0.3.1"` and its two `driver.rs` pins and `driver_smoke.rs:125`; `pyproject.toml` `version = "0.8.1"`; `cd rust && cargo update -w -p cargo-sensorium -p sensorium-transform` (lockfile only). Run the Rust workspace tests and `driver_smoke` green.

- [ ] **Step 3: HONESTY §11** — replace lines 777–789 (the "And one more the review found…" paragraph) with a paragraph of at most the same length: the `&e` exemption is now a rule about the borrowing call's dropped product (design B1, 2026-09-05), measured by E6⁗ (cite the record and the verdicts by name — PASS/STOP/DISCRIMINATING as measured, never assumed), with the one residual it leaves (23 (d): a callee storing a rendering through a side channel). Check `wc -l rust/HONESTY.md` ≤ 800; if over, move §1 (lines 50–156) to `rust/HONESTY-OUTCOMES.md` with a pointer paragraph in its place, the way §8's list moved.

- [ ] **Step 4: Blind spots, index, TRACE-FORMAT** — `rust/HONESTY-BLIND-SPOTS.md` item 23: (c) rewritten as *repaired 2026-09-05 (design B1), measured E6⁗ …, pinned by `arms.rs` rows and `corpus/rust/err_borrowed_into_value`*; add (d) the side-channel residual, *pinned as today's reading by `a_dropped_call_that_stores_what_it_is_handed_is_still_handled_and_says_so`; untested by fixture on a real tree*. `rust/HONESTY-INDEX.md`: the §11 SWALLOWED row's falsifier column gains `E6⁗-A/E6⁗-WS/E6⁗-WS0 (2026-09-05 e6q record, <verdicts>)`, and the chain-identity row gains `corpus/rust/keep_first_error`. `docs/TRACE-FORMAT.md` §5 `translated` row: append *"(Since 2026-09-05 the exit hop at an `err` close goes to the held chain whose text the RETURN carries; before that it went to the innermost, which could label the wrong chain `translated`.)"*.

- [ ] **Step 5: The rung-3 design's dated pointers** — exactly the three lines design §8 specifies, plus R16 (vii): *"(vii) added 2026-09-05: a callee handed `&e` at a dropped call site that STORES a rendering through `&self`, a capture or a global is invisible — blind spot 23 (d)."* Nothing rewritten.

- [ ] **Step 6: CHANGELOG 0.8.1 and CARRIED-DEBT** — `CHANGELOG.md`: a `## 0.8.1 — <date>` block: the rule (with the before/after clone census), the hop, the two corpus cases, the E6⁗ record with its verdicts in the words §4 used, crates 0.3.1. `docs/CARRIED-DEBT.md`: a new dated section (*Settled* / *Deferred, awaiting rulings* / *Process lessons*), and in the 2026-09-05 section strike through (never delete) the `&e` item, the two-held-chains item, and the "different sets" item **only if** E-flip's `changed_equals_delta` read true (else annotate it with the measured numbers and leave it open). If WS0 read NOT DISCRIMINATING, the `&e` item stays open with that fact.

- [ ] **Step 7: Full suite, PR body, commit**

```bash
cd /home/brice/workspace/sensorium/rust && CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target cargo test --workspace 2>&1 | grep -E "^test result|FAILED" && CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target cargo clippy --workspace --all-targets -- -D warnings 2>&1 | tail -1 && cargo fmt --check && cd .. && \
SENSORIUM_CARGO_SENSORIUM=/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/corpus-target PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q 2>&1 | tail -2 && wc -l rust/HONESTY.md rust/tests/mechanics.sh
```
Expected: all green; both files ≤ 800. Write `<ledger>/pr-body-draft.md` (what changed, the verdicts, the residuals, the do-not-merge-if list). Commit by explicit path: `chore(release): sensorium 0.8.1 / transform+driver 0.3.1; CHANGELOG; CARRIED-DEBT; HONESTY §11 repaired clause; design pointers`.

---

### After Task 6 — final review, fix wave, PR

Whole-branch review (fable) on `git diff d1b1b57..HEAD` with the design and the record; findings ruled in the ledger; ONE fix wave (doc/test only after the lock — any code finding is recorded, not repaired); scoped re-review; `git push -u origin feat/rung3-borrow-repair`; `git fetch && git rev-parse HEAD origin/feat/rung3-borrow-repair` equal; `gh pr create` against `main` with the PR body; CI watched to green (the runner's toolchain is pinned 1.96.0; if clippy reddens, fix on the branch). Merge is Brice's. Close-out: delete `/mnt/extra/sensorium-rung2/ws-plain-target` and `tmp/ws-plain-20260905`; keep the control target and base worktree until merge, then `git worktree remove /mnt/extra/sensorium-rung2/base-d1b1b57`.

## Self-review

- **Spec coverage**: B1 → T1; B2 → T1 (the 23 (d) row) + T6; B3 → T2 + T3 (`keep_first_error`); B4/B5 → T4 (runner, §1) + T5 (measurement, discrimination verdict); B6 → T6; B7 → T6; B8 → Global Constraints + every task's commit steps. Design §2's rows → T1 Step 1 verbatim; §3's falsifiers → T2 Steps 1/5 + T3; §4's table → T4 Step 7; §5's corpus → T3; §7's exclusions untouched.
- **Placeholders**: `<N1>`..`<N5>` and `<sha>`/`<verdicts>` are values the ledger supplies at the step named; no step says "add appropriate…".
- **Type consistency**: `phase_e6prime(paths, cfg, tail=("--lib",))` (T4 Step 1) is what T4 Step 4's `phase_arm` calls; `arm_paths_for`, `flip_diff`, `lines_at_flipped_sites`, `ARM_A/ARM_WS/ARM_WS0`, `assemble_e6q` are named identically in Steps 2 and 4; `is_shared_borrow_of_name`, `walk_dropped_call`, `visit_arg`, `is_wild` in T1 Steps 3 and 6; `preferred` in T2 Steps 3 and 7 and T3 Step 7.
