# E4″ — gaps, and what the record does not license

§5 of [`2026-09-08-sensorium-rung4-e4pp.md`](2026-09-08-sensorium-rung4-e4pp.md)
carries the ruling; this file carries the list it links, in a sibling so the
record stays inside the project's 800-line ceiling. Nothing here re-derives a
number: every value is quoted from
`2026-09-08-sensorium-rung4-e4pp.results.json`, from the raw record beside it in
the plan ledger, or from the E4′ record it cites. **Every fix below is ruled for
the NEXT slice and none is applied to this one** — §1.4's kill 6 forbids an
instrument change after the measurement that would make a cell come out
differently, which is the whole reason a pre-registration is worth having.

## The instrument's own gaps, as this run exposed them

1. **The corpus-case reader compares a bare name against a prefixed listing —
   and prints `False` rather than `null`.** `H8.spawned_test_fn` is the bare
   `refocus_spawned_test_fn`; `raw_h8.case_listing.names` holds **63** names and
   spells the Rust ones `rust/<name>` (43 of the 63 carry that prefix),
   `rust/refocus_spawned_test_fn` among them. The membership test therefore
   answered **`False`** — `H8.spawned_test_fn_present` — where the case was in
   fact collected, run through the built driver under `--require-driver` and
   equal (`H8.corpus_rc` 0, `corpus_skipped` empty, `H8.spawned_test_fn_skipped`
   empty). **This is the named bug class**: a probe that could not read a thing
   the way it asked for it must record `null` **with its reason**, never a clean
   negative that a reader cannot tell from a real absence. It is also E4′ gap 3
   one turn on — there the same reader returned `null` because the collector
   exposed no list at all; this slice gave it a list, and the reader began
   printing a measured-looking `False` instead. **Fix, next slice:** match on the
   listing's last path segment as well as the whole name, and when neither
   spelling is found record `null` carrying `case_listing.command` and its `rc`
   as the reason. One comparison and one fallback; the numbers in this record
   need no re-deriving, because `case_listing.names` already holds the answer.

2. **The STOP's label is fixed per endpoint, not derived from what failed.**
   `stop` and the `e4pp.FAILED` marker both end *"This is a STOP of the
   subject"*, and `H7.stop_is_of_the` carries the instrument's wording — the two
   sentences are attached to the endpoint id rather than to the cell that
   missed. §1.4's kill 2 draws exactly this distinction and asks the record to
   keep it. On this run's evidence the H8 miss is the **instrument's** (three
   green return codes, a case that ran), so the marker's own words point at the
   wrong side. **Fix, next slice:** name the STOP by what the failing cell
   measures — the subject when a subject cell missed, the instrument when a
   reader did — and print both when they disagree, as §4 does here by hand.

3. **`driver_version` is read on one side, and §1.5 reads as though it were
   two.** The instrument reads the re-run trace's `meta.driver_version` —
   `cargo-sensorium 0.5.2` on **69 of 69** rows
   (`pairs.rows[*].driver_version_from_the_trace`) — and the built driver's own
   token and sha256 (`reported.driver_version`). It never opens the **copied
   original** for its `meta`, so the originals' `0.5.0` appears nowhere in the
   raw or assembled record: it is §1.1's pre-registered fact, carried from E4
   (E4′ §2 read `0.5.1` on its own re-runs, by the same route).
   **The key names diverge too:** §1.5 and `reported.driver_version.note` say the
   token is read from `meta.recorder`, while the reader takes
   `meta.driver_version` (`rust/tests/acceptance_e4p_phases.py:294`) — and
   `meta.recorder` on these traces reads `sensorium-rt 0.4.0`, the runtime, not
   the driver; §2 and §4 quote the accurate key, and the pre-registration's
   sentence is recorded here rather than edited.
   §1.5's sentence — *"`driver_version` on both sides"* — is satisfiable by
   reading "trace and built driver" as the two sides, and that is what the
   instrument did; a reader who takes "sides" to mean the pair's two runs finds
   one. The claim the record actually stands on is not affected, because the
   **rt hash is read on both sides and differs on 61 of 61** — that, not a
   version token, is what proves the two builds are not the same build. **Fix,
   next slice:** read `meta.driver_version` from the copied original too and
   publish the pair beside the rt-hash pair, so the sentence and the cells say
   the same thing.

4. **H2's fragment count was read on both sides and published on neither.**
   §1.4's H2 row pre-commits two second readings: the rt hash each side carries,
   and *"the count of fragments removed per key per side"*. The first is a cell
   (`H2.hashes_differ`, `H2.hashes_unread`, `reported.rt_hashes`). The second
   exists only in the raw: `raw_pass2.refocuses[*].original_rt_hash.fragments`
   and `.rerun_rt_hash.fragments` are **1** on 61 of 61, with `occurrences` **2**
   on both sides — one fragment spanning the `--extern` and the `-L dependency=`
   tokens, exactly the shape R1 strips. `endpoints.H2` carries no fragment cell
   and `reported.rt_hashes.by_pair[*]` carries `original` and `rerun` values
   only, so a reader who opens the record for a pre-committed reading finds it
   absent and must go to a gitignored ledger. Same class as gap 3: measured, not
   published. **Fix, next slice:** lift both counts into `H2` as a `{value, n,
   lens, dropped}` cell and into `reported.rt_hashes.by_pair[*]` — the numbers
   are already read, so nothing is re-measured.

5. **`reported.walls_s` holds three of the four walls §1.5 names.** The bullet
   pre-commits *"wall per arm (A, B, C and the dry run), the first focus
   distinguished from the later ones with cargo's own build time inside each,
   and the driver build's wall separately"*; `reported.walls_s` has `A`, `B`,
   `C` and a `note`. The missing pieces were all recorded, just not gathered
   where the pre-registration points: the driver build's wall is
   `pins.built_from.cargo_wall_s` (**0.025 s**, `rebuilt: no`), cargo's own time
   inside each refocus is `raw_pass2.refocuses[*].cargo_finished_s` (a per-row
   list, ~3.3 s typical), and the dry runs' walls stayed in their own archived
   results rather than being carried into the real run's `reported`. Nothing is
   gated on a wall, so no verdict moves — but a bullet naming four readings
   beside a field holding three is the gap. **Fix, next slice:** add
   `walls_s.driver_build`, `walls_s.dry` and a per-arm cargo-time summary, all
   from fields this run already writes.

## What this record does NOT license

- **The harness anchor R3 is not measured by these 61.** Blind spot 28's live
  direction is *upward*: `#[test] fn` is an ordinary fn to rustc, so
  `thread::spawn(|| a_test_fn())` puts a **marked root** on a thread the program
  started, that thread is subtracted as the recorder's own,
  `threads_started − harness` can reach 0, no thread caveat is emitted and the
  licence is **granted over a program thread** — the direction that claims more.
  Producing it needs a test that spawns *through a marked fn*. The four
  thread-spawning pairs in this subject do not: §1.2 reads them from the
  clone's source — `a_pager_can_be_shared_across_threads` spawns one ordinary
  closure, and the three `pager_refusal_advice_test` tests reach four workers
  through `serve_fake()` — so **none of the 61 can exercise the mechanism**, and
  H1's PASS says nothing about it either way. What checks R3 is
  `corpus/rust/refocus_spawned_test_fn`, one case of `H8.corpus_cases` = **63**,
  which ran green through the built driver under `--require-driver` — evidence
  at **n = 1**, from the corpus, not from this record's n = 61. It is also the
  case the cell in gap 1 failed to find by name, so the one place R3's evidence
  lives is the one place this instrument misread.
- **Nothing about a fresh recording.** Pass 1 was not re-run; the 61 originals
  are E4's bytes, copied and never written, and every difference this record
  reads is the reader's and the driver's.
- **Nothing about a Python pair.** R1 strips a fragment only a Rust driver
  injects; no Python trace can carry it, and no Python pair was read here.
- **Nothing about a larger session set.** K was **1**, so `H4.names_bounded` is
  empty and `H4.decided_on_k_alone` is `false`: the by-name half was read in
  full and kill 7's reduced reading never applied. A box whose session set
  exceeds the printed line's 8-name cap is unmeasured by this record.
- **Nothing about what the licence can see.** The four counts stay in kind and
  unsummed — source, environment and exit **verified** on 61; output and
  children **UNVERIFIABLE by construction** on 61 (`H7.licence_verified_counts`).
  This slice changed the licence's thread and environment arithmetic, not its
  reach.
- **Nothing about a wall.** No endpoint is derived from one, and
  `reported.walls_s` is published for the reader, not for a gate.
- **No cell went unmeasured.** E4′ had to publish 57 unparsed program-thread
  readings inside `H1.withheld.value`; none of them is here
  (`H1.counts_source_by_name` reads `licence-clause` on 61 of 61), and no
  measurement cell this run wrote carries a `dropped` reason.
- **E4 and E4′ are not re-opened.** E4′'s `granted` = 0 stands as E4′'s reading
  of E4′'s run; this record measures the same partition after the confound E4′
  named was removed, and does not correct a number in either.

## The E4′ gaps this instrument closed, and the cells that carry them

| E4′ gap | what it was | closed by, in this record |
|---|---|---|
| **1** | the licence partition read `None` on any pair with no program thread, so `harness_threads_all_one` came back **false** over 61 pairs each reporting one, and two second readings (`sides_disagree`, `reasons_that_never_subtracted`) were 4-wide rather than 61-wide | `H7.headline` = **0** null partition cells over n **69**; `H7.counts_carry_their_source_line` **true** over 69 with `counts_without_a_source_line` empty; `H1.counts_source_by_name` = `licence-clause` on **61 of 61**; `H1.harness_threads_all_one` **true** over 61; `H1.hides_the_exclusion` and `H1.reasons_that_never_subtracted` both empty **over 61** |
| **2** | `sensorium_version` recorded as an empty string — a failed probe that read as measured | `H7.version_probe` = **`0.8.5`** with `version_probe_ok` **true** and `version_probe_reason` `null`; §1.4's own gate forbids the empty string, so a blank would have been a STOP of the instrument rather than a lens note |
| **7** | `reported.licence_verified_counts` permanently `null` — built from a top-level key the runner never wrote | `H7.licence_verified_counts` **non-null** (source 61, environment 61, exit 61 verified; output 61, children 61 unverifiable; n 61) and `reported.licence_verified_counts` carrying the same object, so the field the record names is the field a reader finds |

E4′'s gaps **4**, **5** and **6** are about E4′'s own renderer, lock test and
sidecar census and are not this instrument's to close; **3** is gap 1 of the
list above, one turn on rather than closed.
