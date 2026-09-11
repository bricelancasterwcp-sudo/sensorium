# The TypeScript recorder's honesty ledger — §9: Cost

Section 9 of [`typescript/HONESTY.md`](HONESTY.md), **moved here 2026-09-11
(S5 rung 4, the focus tier) so that file stays under 800 lines**, on the
precedent [`HONESTY-BLIND-SPOTS.md`](HONESTY-BLIND-SPOTS.md) set 2026-09-10 and
[`../rust/HONESTY-ERR-FLOW.md`](../rust/HONESTY-ERR-FLOW.md) before it. §9 is
the section that grows at every rung — three **Measured** blocks already, one
per rung, and rung 4 owes a fourth — so it is the split chosen deliberately
rather than one discovered at the ceiling. **The wording, the order and the
numbering are unchanged**, so `§9` still names what it always named, one file
away — including from the ledger's own index, whose three `| 9 |` rows stay
where they are, in `typescript/HONESTY.md`.

## 9. Cost

**The promise.** Cost is a reported fact with its `n` and its lens beside it,
and it gates nothing.

The tier is a runtime gate and the transform runs every time, so the whole cost
of `--tier off` is the transform — which makes `off` a real control arm rather
than a different program. The endpoints report walls at n=5 per arm,
interleaved, conversion excluded, and report conversion separately. Where an
endpoint carries a bound, crossing it buys **work**, not a verdict: a transform
cache keyed on source sha becomes rung-1 work if `off/plain` goes above 1.10,
and a conversion wall above the plain suite's own wall is a design input
naming a Node converter or a binary wire. Neither outcome is a NO-GO, and
neither number is allowed to decide whether the recorder is honest.

**Measured, rung 1** *(added 2026-09-09; every number from
`../docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.md` §3, on one
lens: the VTT frontend at `0091e97` — 372 test files, 4,278 tests — under
vitest 4.1.9, vite 6.4.3, jsdom 29.1.1, node v24.16.0, 16 cores)*:

- **Recording**: `off/plain` **1.0587** and `call/plain` **1.1324**, n=5 per
  arm, interleaved, 0 runs dropped, conversion excluded — inside E1′'s 1.10
  bound, so the transform stays uncached and the source-sha cache stays a later
  slice. Beside them, ungated: **99.61 B/line** and **162,629.8 lines/s** under
  the product runtime (medians over the 5 call runs), and vitest's own
  `transform` seconds **10.24 / 21.64 / 21.43** for plain / off / call.
- **Conversion**: full-suite `ingest` over 372 spools and 414,450,522 bytes,
  **45.5293 s** median (n=3) against the same run's plain wall of **22.5925 s**
  — ×2.02, **above** E10's bound. E10's own rule made that a **design input and
  not a STOP**, and the input is taken: a Node converter on `node:sqlite`, or a
  binary wire, is the next slice's question. One file's spool converts in
  **0.3638 s** (n=3), which is what a debugging loop actually pays, and it is
  reported here beside the suite number so the design question is asked about
  the right workload.
- **Reading**: `info` **0.5401 s** and `diff` **0.6867 s** (n=3 each) on the
  lens's largest trace, 333,832,192 bytes.
- **And one cost that is a STOP.** E6′ asks whether a plain run afterwards is
  contaminated, in four clauses. Three ask about contamination directly and all
  three hold — the sources are identical by sha256 manifest (**748 OK, 0
  FAILED**), **0** `__srt` markers appear in any cache directory, and
  `node_modules/.sensorium` is **absent**. The fourth is a timing clause, and
  it **STOPped**: the plain-after wall **22.8678 s** against the plain arm's
  own min–max band **[22.3136, 22.7221]**, 0.1457 s (0.65%) above it. The
  number stands as measured — nothing was re-rolled and no band was moved —
  and what the STOP is understood to rest on is written down rather than
  argued away: the instrument that took it ran with no load guard though its
  clause is a timing clause, and a five-run min–max is a range and not a
  tolerance (record §5, gaps 5 and 6). It is re-measured next slice under a
  NEW pre-registration, **E6″**. **The rung therefore ships DONE-WITH-STOP**,
  which is the phrase the record, the spec, the CHANGELOG and both READMEs use
  for it, so a reader meets one name for one fact. This ledger states it as a
  STOP because that is what the pre-registration's own words make it, and a
  rung that ships with one is a rung that ships with one.


**Measured, slice 2** *(added 2026-09-10; every number from
`../docs/superpowers/acceptance/2026-09-10-sensorium-s5-slice2.md` §3 and §4,
on the same lens)*:

- **Conversion, the ladder.** Rung 1's design input was taken and answered on
  the pinned 372-spool, 414,450,522-byte copy of one recording, every cell
  guarded and each lever measured before the next was written. **Arm 0** (the
  0.9.0 converter): full suite at 16 jobs **45.7378 s**, the one file
  **0.3624 s**, the heaviest worker's peak resident **2,273,872 kB** on the
  big-spool cell. **A1** — one transaction per trace, `synchronous=NORMAL`:
  **17.7740 s** and **0.1647 s**, RSS unmoved at **2,273,996 kB** (it is not
  the quantity this lever touches). **A3** — the streaming spool reader:
  **16.5088 s** and **0.1628 s**, and peak resident **280,408 kB** on that
  same cell, **8.1096×** below A1's. **A2** (largest-first dispatch) and **A4** (the per-record Python
  cost) were **not built**: the spec conditioned them on the first two levers
  leaving the suite above the bound, and they did not; a lever that cannot
  move a verdict is not free.
- **Conversion, the verdicts.** **E10′-suite PASS** — **16.3859 s** median,
  n=5, against the pinned **22.5925 s** wall: **the converter stays Python**
  and Arm B is not raised. **E10′-file PASS** — **0.1648 s** median, n=5,
  against **0.4002 s**, which was the one clause on this ladder allowed to
  **STOP** it; it did not fire. **E10′-eq PASS** — the set converted twice,
  **372 MATCH / 0 DIVERGED / 0 REFUSED**, the only `meta` key differing on any
  pair being the minted `run_id`. Beside it, reported and never gated,
  **E10′-eq-content**: every row of all seven tables compared column for
  column, **372 / 372 identical**.
- **One cost this slice does not have a number for.** The non-durable writer
  holds a whole trace's WAL until `close()`: measured once at `--jobs 1`, a
  **335,895,392-byte** `-wal` beside a **333,832,192-byte** database, so
  transient disk is ≈ **2×** per in-flight trace and, at the default job
  count, the sum over the workers building at that moment. Nothing came near
  the disk on any cell here (63 GB free), so no verdict rests on it — but this
  box has run at ~3 GB free, and the peak at 16 jobs is unmeasured. It is in
  `docs/CARRIED-DEBT.md`.
- **And the STOP is answered.** E6′'s plain-band clause STOPped at rung 1.
  **E6″ — PASS**, on all five clauses of a NEW pre-registration: manifest
  **748 OK / 0 FAILED** before and after, all ten plain runs at
  `372 passed (372)` / `4278 passed (4278)` with **nothing dropped**, **0**
  `__srt` markers over the 2 cache directories that exist, the wrapper
  **absent**, and the after arm's median **22.1136 s** inside the band
  **[21.9834, 22.3652]** the before arm's own median (**22.1743**) and range
  (**0.1909**) define — 0.0607 s **faster**, not slower. The instrument E6′
  lacked is what makes this readable: a load guard on every timed run with its
  reading in the artifact, a band derived from the arm rather than chosen, and
  medians over n=5 on each side. What it closes is one session, one lens, one
  recorder, and the record's §5 says what it does not settle — the band's
  width is a property of the session, and "under 4.0" is not "idle".

**Measured, rung 2** *(added 2026-09-10; every number from
`../docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2.md` §3, on the
same lens, with a load guard on every timed run and its reading beside every
wall — the highest 1-minute load any arm ran under was **3.91**)*:

- **Recording, again.** `off/plain` **1.0608** and `call/plain` **1.1266**,
  n=5 per arm, interleaved, 15 of 15 runs green, conversion excluded (`E1‴`).
  Rung 1 read **1.0587** and **1.1324** on the same lens with a recorder that
  did not yet splice a `catch` word, a callback wrapper or a `finally` sink,
  so the throw flow's whole cost is inside the difference between those two
  pairs — which is to say inside the noise this instrument can resolve. It
  gates nothing either way, and the transform stays uncached.
- **Conversion, again.** The rung's own 372-spool set (**414,599,103 B**)
  converts in **16.0715 s** at 16 jobs (n=5), and its `useMeshVoice` spool
  (**611,325 B**) in **0.1642 s** (n=5) — beside slice 2's **16.3859 s** and
  **0.1648 s** on the pinned set (`E10″`). No gate; the converter stays
  Python.
- **What the recorder wrote about throws, over 372 member traces.** HANDLED
  records by `how`: `catch` **36**, `catch_callback` **182**,
  `catch_escaped` **22**, `sink_empty_catch` **37**,
  `sink_empty_catch_callback` **8** — **285** in all, from **287** spliced
  sites of **287** eligible (`E2″`, ratio **1.0000**, zero named exclusions).
  The escape rule's own verdict distribution over that lens: **22 of 177**
  catch clauses read `catch_escaped` — **0.1243** — with `catch` **87** and
  `sink_empty_catch` **68** beside it. Reported, gated by nothing.
- **And what the rules made of it.** Over the same run, `swallowed` **261**
  and `ambiguous` **53** across **314** raises in **53** of 372 processes;
  **30** SWALLOWED shapes printed, every one hand-adjudicated, **0** of them
  false (`E6-TS′`). Fifteen of the thirty needed a second reading, and
  **13** of the 30 AMBIGUOUS shapes read the escaped-handler reason. What
  those numbers do NOT establish is a false-negative rate: the gate asks
  whether an accusation is true, and a swallow this recorder never saw makes
  no shape to adjudicate.

**Falsifiers.** `E1′`, `E10`, `E10′`, `E6′`, `E6″`, `E1‴`, `E10″`, `E2″`,
`E6-TS′`.
