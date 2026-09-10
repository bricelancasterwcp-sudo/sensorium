# E6-TS′ — the adjudication: every SWALLOWED shape the lens sweep printed

One guarded call-tier run of the VTT frontend's whole suite (372 files, 4278
tests) through `sensorium 0.9.1` / `sensorium-ts 0.2.0` at commit
`3db0f28a655e6e8ccb6a4d1bb8c1260bb03dabe7`, then `exceptions <invocation>
--limit 10000`. The answer printed **60 shapes — 30 SWALLOWED and 30
AMBIGUOUS** — over a tally of `swallowed 261, ambiguous 53`. Nothing was
paged (no `more:` note), so every SWALLOWED shape the answer holds has a row
below.

The transcript is committed beside this file as
`…-e6tsp-exceptions.txt`; the sites below are lens-relative
(`src/…`), the transcript's own verdict lines name `qualname L<line>` and
each row's `file:line` was resolved from the sink event in the trace the
bracket names, not from the printed text.

## The rule this table applies, quoted from §1 (byte-locked before any line was read)

> a SWALLOWED line is **true** when the catch (or callback, or `finally`)
> discarded the failure and the caller went on as if the call had succeeded —
> an empty clause, a clause that only logs, a `finally` that returned; it is
> **false** when the failure or a rendering of it reached the caller by any
> route the rule did not see — returned, stored, asserted on, rendered into a
> value, re-thrown as another object, or read by a handler the rule called
> opaque and that in fact propagated. Every line is read against the source
> at the site the verdict names; the count of lines and the adjudication of
> each are in the record, and a line the adjudicator cannot decide from the
> source counts as false.

**The one reading this table had to settle, and how.** Fifteen of the thirty
clauses send the caller a CONSTANT on failure — `setError('Could not load the
turn.')`, `return fallback`, `setConfigured(false)`, `ok = false`, `return
undefined`. Ten of those fifteen do not even bind the exception. The question
§7 asks is whether *the failure or a rendering of it* reached the caller, and
a constant chosen by the programmer is neither: it is identical whatever was
thrown, and it carries no type, no message and no site. §7 settles the
direction itself by putting **"a clause that only logs" on the TRUE side** —
a `console.warn(e)` hands the WHOLE error to a channel a human can read,
which is strictly more of the failure than `setError('…')` transmits
anywhere. A reading that called the constant-signal clauses false while
calling the logging clauses true would be non-monotone in the one quantity
the rule is about. So the constant-signal family is TRUE, and each such row
is marked as having needed a second reading.

The clauses the rule does NOT call swallowed are the counterpart: `catch (e)
{ setError(e.message) }`, `return String(e)`, `list.push(e)` are
`catch_escaped`, and every one of them printed AMBIGUOUS in this same answer
(13 of the 30 ambiguous shapes carry the escaped reason).

## The table

| id | site | how | source | verdict | second reading | reason |
|---|---|---|---|---|---|---|
| S1 | src/hooks/useAiAssist.ts:56 | catch_callback | `.catch((error: unknown) => { console.warn('[useAiAssist] AI settings probe failed; will retry on next mount', error); subscribers.forEach((notify) => notify(false)); })` | TRUE | no | The binding reaches `console.warn` and nothing else; subscribers are notified with the constant `false` (fail-closed), which is the same value a genuinely unconfigured instance produces. §7's "a clause that only logs". ×130 over 11 processes. |
| S2 | src/lib/builder/useBuilderContent.ts:72 | catch_callback | `.catch(() => { if (!cancelled) { setRows([]); setError(true); } })` | TRUE | yes | Parameterless: the handler cannot render the failure. `setRows([])` and `setError(true)` are constants; a consumer of the hook learns that something failed and nothing about what. Nothing of the error reached the caller. |
| S3 | src/stores/roomStore.tokens.ts:554 | sink_empty_catch | `} catch { // Empty/non-JSON body (e.g. 204) — nothing to thread. }` | TRUE | no | An empty clause; the `SyntaxError` from `r.json()` (untraced) is discarded and `saveTokenPosition` returns. A deliberate swallow is still a swallow — §7 asks whether the failure was discarded, not whether discarding it was wise. |
| S4 | src/components/inventory/InventoryTab.tsx:59 | catch | `} catch { return; }` | TRUE | no | No binding; the handler returns and the drop silently does nothing. The `JSON.parse` failure reaches no channel. |
| S5 | src/components/pf2e/SpellCastControl.tsx:406 | catch_callback | `const body = await r.json().catch(() => null);` | TRUE | yes | Parameterless handler returning the constant `null`; `body` then flows into `detailMessage(body, '…the server refused it.')`, which produces the FALLBACK message. The parse failure is invisible to every caller. Receiver is a promise (`r.json()`). |
| S6 | src/components/shell/PlayerView.tsx:385 | sink_empty_catch_callback | `}).catch(() => {});` | TRUE | no | An empty rejection handler on a promise chain. The textbook shape. |
| S7 | src/lib/leveling/startingLevel.ts:72 | catch | `} catch { return fallback; }` | TRUE | yes | No binding; the function returns the caller-supplied `fallback`, indistinguishable from the server having returned those values. Classic swallow. |
| S8 | src/components/compendium/ItemEditor.tsx:47 | sink_empty_catch | `} catch { // fall through to substring extraction below }` | TRUE | no | An empty clause; `extractJsonObject` recovers by a second route and returns. The caller never learns the direct parse failed. |
| S9 | src/components/TurnCard.tsx:198 | catch | `} catch { if (!cancelled) setError('Could not load the turn.'); }` | TRUE | yes | No binding; a fixed string is set into component state. Nothing of the error — type, message or site — reaches anything. Constant-signal family. |
| S10 | src/lib/combat/restFlow.ts:84 | catch | `} catch { reportPersistError('Rested, but the game clock could not be advanced (network error).'); }` | TRUE | yes | No binding; a constant message goes to the persist-error sink. The thrown value is discarded and `advanceGameClock` returns. |
| S11 | src/hooks/useAiAssist.ts:56 | catch_callback | same clause as S1 | TRUE | no | Same site, same clause; printed as its own shape only because the sink's frame id is `f128`, which the grouper's mask does not mask (see §5's gap). Same verdict for the same reason. |
| S12 | src/components/map/useGridDetect.ts:179 | catch | `} catch { // Load/decode failure or tainted canvas -> the same reliable fallback. fallback(); }` | TRUE | yes | No binding; `fallback()` takes no argument, so nothing of the error can travel with it. The caller sees the fallback grid and not the failure. |
| S13 | src/components/ai-prep/VoiceTool.tsx:25 | catch | `} catch { setError('Could not synthesize speech.'); } finally { setLoading(false); }` | TRUE | yes | No binding; a fixed string into state. Constant-signal family. |
| S14 | src/hooks/useActionGuard.test.tsx:29 | sink_empty_catch_callback | `onClick={() => void run(onAct).catch(() => {})}` | TRUE | no | An empty rejection handler; the file's own comment says "the rejection is absorbed at the call site". `run` returns a promise. |
| S15 | src/hooks/useLiveKit.ts:88 | catch_callback | `.catch(() => { if (!cancelled) setConfigured(false); });` | TRUE | yes | Parameterless; `false` is the constant a genuinely unconfigured room also produces. Nothing of the failure reaches the hook's consumers. |
| S16 | src/components/VoiceControls.tsx:266 | sink_empty_catch_callback | `.catch(() => {});` | TRUE | no | Empty handler on a `Promise.resolve(apiFetch(…))` chain. |
| S17 | src/hooks/useAiAssist.ts:56 | catch_callback | same clause as S1 | TRUE | no | Same site and clause; a separate shape only because the sink's frame id is `f32` (§5's gap). |
| S18 | src/hooks/useWebSocket.ts:1143 | catch_callback | `.catch((err) => console.error('[ws] state resync failed', err));` | TRUE | no | The parameter is an argument of `console.error` and nothing else. §7's "a clause that only logs". ×34. |
| S19 | src/hooks/useMeshVoice.ts:506 | catch | `try { voiceFxRef.current = createVoiceFx(stream); } catch { voiceFxRef.current = null; }` | TRUE | yes | No binding; a constant `null` is assigned and the join proceeds on the raw mic. The source's own comment says the failure is non-fatal. ×19. |
| S20 | src/components/onboarding/SetSceneCard.tsx:57 | sink_empty_catch_callback | `.catch(() => {});` | TRUE | no | Empty handler on an `apiFetch` chain. |
| S21 | src/components/onboarding/SetSceneCard.tsx:78 | catch | `} catch { setError('Map upload failed. Try again.'); }` | TRUE | yes | No binding; a fixed string into state. Constant-signal family. |
| S22 | src/stores/roomStore.ts:2337 | catch | `} catch (e) { // Deliberately swallowed after logging — see the doc comment above. console.warn('[scenes] could not attach the uploaded map to a scene', e); }` | TRUE | no | The binding reaches `console.warn` and nothing else. The source says the word itself. |
| S23 | src/hooks/useDraggable.ts:22 | sink_empty_catch | `} catch { /* private mode / bad JSON — fall through */ }` | TRUE | no | An empty clause; the initializer falls through to `fallback()`. |
| S24 | src/lib/clipboard.ts:17 | sink_empty_catch | `} catch { // Permission denied or transient failure — try the legacy path below. }` | TRUE | no | An empty clause; control falls through to `legacyCopy(text)`. |
| S25 | src/lib/clipboard.ts:41 | catch | `} catch { ok = false; } finally { … }` | TRUE | yes | No binding; `ok` is a constant `false` and is what the function returns. The caller learns copying failed and nothing about why. Constant-signal family. |
| S26 | src/lib/modules/hooks.ts:98 | catch | `} catch (err) { console.error(...template naming event.type..., err); }` — the clause's only statement, after a comment reading "A throwing hook must not break delivery to other subscribers" | TRUE | no | The binding is an argument of `console.error` and nothing else. §7's "a clause that only logs". |
| S27 | src/stores/roomStore.ts:2689 | catch | `} catch { set((s) => ({ drawings: s.drawings.filter((d) => d.id !== tempId) })); }` | TRUE | yes | No binding; the optimistic drawing is rolled back and the action returns. The drawing vanishes and no channel says why. |
| S28 | src/stores/roomStore.assets.ts:61 | catch | `} catch { return undefined; }` | TRUE | yes | No binding; `undefined` is the same value the `!res.ok` branch returns, so a network failure and a refused upload are indistinguishable to the caller. |
| S29 | src/stores/roomStore.assets.ts:81 | catch | `} catch { return undefined; }` | TRUE | yes | As S28, in `tokenizeAsset`; the source says "same fix, same reasoning". |
| S30 | src/lib/appearance.ts:80 | catch | `} catch { return { ...DEFAULT_PREFS }; }` | TRUE | yes | No binding; the defaults are returned, indistinguishable from a browser that had never stored preferences. |

## What the table comes to

| | |
|---|---|
| SWALLOWED shapes printed | **30** |
| adjudicated TRUE | **30** |
| adjudicated FALSE (the gate) | **0** |
| needed a second reading | **15** — the constant-signal family (S2, S5, S7, S9, S10, S12, S13, S15, S19, S21, S25, S27, S28, S29, S30) |
| escaped-ambiguous shapes, reported beside the gate | **13** of the 30 AMBIGUOUS shapes |
| per-disposition tally (units, not shapes) | `swallowed 261, ambiguous 53` |

**The declared blind spot that did not fire.** Task 2 ruled that
`.catch(x)`/`.then(x, y)` are wrapped on ANY receiver, so a non-promise API
with a method named `catch` could write an orphan HANDLED and reach
"SWALLOWED, born outside a throw statement" — a false accusation by §7. Every
one of the eleven callback shapes above (S1, S2, S5, S6, S11, S14, S15, S16,
S17, S18, S20) has a promise receiver: an `apiFetch`/`fetch` chain, a
`Promise.resolve(…)` chain, `r.json()`, or an `async` function's return. The
blind spot is real and is declared; it did not fire on this lens.
