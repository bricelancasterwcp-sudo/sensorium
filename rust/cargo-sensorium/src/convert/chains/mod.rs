//! The chain machine (design R7 and §2a of
//! `docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md`):
//! per-thread state × next record, in one pure function.
//!
//! **What this module decides, and what it refuses to decide.** It mints chain
//! IDENTITY -- which recorded `Err` is a continuation of which, how many frames
//! it crossed, whether the type changed on the way, and whether it was born in
//! instrumented code or arrived from a dependency -- and it records the FACT of
//! how each chain ended ([`Terminal`]). It does not compute dispositions: no
//! `SWALLOWED`, no `AMBIGUOUS`, no verdict of any kind. Those are the Python
//! rule module's (design R11, placement B), and a converter that rendered them
//! would be the second place a verdict is written.
//!
//! [`Terminal::SwallowedCandidate`] is named the way it is for that reason: it
//! says a sink absorbed the chain and its holder frame then returned `ok`,
//! which is what a SWALLOWED verdict is made OF, not the verdict.
//!
//! **Purity.** [`mint`] takes one thread's records, already resolved against
//! the manifest, and returns events. It opens no file, reads no clock and
//! touches no SQLite; the frame stack it walks is its own simulation of the
//! CALL/RETURN records it was handed, so a test can state a thread's shape as
//! data and read the chains back.
//!
//! **Where §2a is refined, and why.** The table is written for the one open
//! chain whose holder is the frame a row names; a frame can hold more than one
//! (a nested chain hops up into it). This module applies the row to EVERY
//! chain the closing frame holds, innermost first, which is what makes the
//! table total. And a chain whose sink already fired does NOT hop when its
//! holder closes `err`/`none`: design R8 names that shape ("handled, then the
//! frame failed for another reason") and gives it its own reading, so it ends
//! here as [`Terminal::HandledThenFailed`] and the `Err` leaving the frame
//! opens a chain of its own -- the `cleanup_then_fail` corpus case.

use crate::convert::spool::How;

/// Err chain serials start here, per thread, so no chain serial can ever be
/// mistaken for a panic serial (design R4/R7: panics are numbered from 1 per
/// thread by `frames.rs`, and the two namespaces must not overlap because an
/// `exc` object carries only `kind` to tell them apart).
pub const FIRST_CHAIN_SERIAL: u64 = 1 << 32;

/// Where the `Err` a chain carries came from.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Origin {
    /// Born at an instrumented site: a `?`, a propagating arm, or a frame that
    /// closed `err`.
    Workspace,
    /// Absorbed at a sink with no chain to continue -- the `Err` was made
    /// somewhere this recording never saw (design R8's "born in dependency
    /// code").
    Outside,
}

impl Origin {
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Origin::Workspace => "workspace",
            Origin::Outside => "outside",
        }
    }
}

/// How a chain's life ended, as a FACT about the record stream. The Python
/// rules turn one of these into a disposition; nothing here does.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Terminal {
    /// A sink absorbed it and the holder frame then returned `ok`.
    SwallowedCandidate,
    /// A sink absorbed it and the holder frame then failed anyway (`err` or
    /// `none`) -- design R8's named blind spot.
    HandledThenFailed,
    /// The holder returned `ok` with no sink seen, or an `arm_ambiguous`
    /// bound it and let the name escape.
    AmbiguousEscaped,
    /// It shared a frame's window with another, different `Err`.
    Merged,
    /// The frame holding it unwound.
    Panicked,
    /// It left a frame whose manifest row is marked `test` or `main`.
    ReturnedToHarness,
    /// It left the outermost frame of a SPAWNED thread -- into a `JoinHandle`,
    /// whether or not anything ever read it.
    LeftThread,
    /// Still open when the thread ended, on a frame that is neither.
    Propagated,
}

impl Terminal {
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Terminal::SwallowedCandidate => "swallowed_candidate",
            Terminal::HandledThenFailed => "handled_then_failed",
            Terminal::AmbiguousEscaped => "ambiguous_escaped",
            Terminal::Merged => "merged",
            Terminal::Panicked => "panicked",
            Terminal::ReturnedToHarness => "returned_to_harness",
            Terminal::LeftThread => "left_thread",
            Terminal::Propagated => "propagated",
        }
    }
}

/// The recorded text of one `Err`: its type and its `Debug` rendering, each
/// `None` when the probe could not read it.
///
/// `None` is a WILDCARD in [`ErrText::matches`], not a value: an
/// `Err(_) =>` arm records neither field (design R4), and reading that as "a
/// different `Err`" would break every chain such an arm sits in. Two `Err`s of
/// one type with identical text in one window are one chain -- the documented
/// limit of having no identity on the wire (R7).
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ErrText {
    pub type_name: Option<String>,
    pub msg: Option<String>,
}

impl ErrText {
    #[must_use]
    pub fn matches(&self, other: &ErrText) -> bool {
        fn same(a: Option<&String>, b: Option<&String>) -> bool {
            match (a, b) {
                (Some(a), Some(b)) => a == b,
                _ => true,
            }
        }
        same(self.type_name.as_ref(), other.type_name.as_ref())
            && same(self.msg.as_ref(), other.msg.as_ref())
    }

    /// Fill in what this text does not know from one that does. Identity is
    /// established by the fields both sides carry, so learning a type at a
    /// later hop never re-opens the question of which chain this is.
    fn learn_from(&mut self, other: &ErrText) {
        if self.type_name.is_none() {
            self.type_name.clone_from(&other.type_name);
        }
        if self.msg.is_none() {
            self.msg.clone_from(&other.msg);
        }
    }
}

/// A frame's outcome as the machine reads it. `Err` here means the wire's
/// outcome 2 AND a type block to go with it (the v3 shape): an untyped `err`
/// close is a v2 spool's, carries no origin RAISE, and is read as
/// [`Outcome::None`] -- see [`Rec::Return`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    Ok,
    Err,
    None,
    Panic,
}

/// One record of a thread, reduced to what the chain machine reads.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Rec {
    /// A frame opened. The marks are its manifest row's (design R1b) and are
    /// what a chain still open at the thread's end is judged by.
    Call {
        test: bool,
        main: bool,
    },
    /// A frame closed. `text` is meaningful only on [`Outcome::Err`].
    Return {
        outcome: Outcome,
        text: ErrText,
    },
    /// A RAISE or a HANDLED; `how` says which and why (design R2).
    ErrFlow {
        how: How,
        text: ErrText,
    },
    ThreadEnd,
}

/// One record with the `seq` the writer will key its event by.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Input {
    pub seq: u64,
    pub rec: Rec,
}

/// Which event at a `seq` a chain fact belongs to: the record's own, or the
/// origin RAISE the converter synthesises IN FRONT of an `err` RETURN.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum At {
    Record,
    ExitBefore,
}

/// What the machine says about one event.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ChainEvent {
    pub seq: u64,
    pub at: At,
    pub serial: u64,
    /// 1-based: the origin event is hop 1, and each frame the chain crosses
    /// afterwards is the next. An event that absorbs or observes a chain
    /// without crossing a frame carries the hop it happened at.
    pub hop: u32,
    pub origin: Origin,
    /// This event's recorded type differs from the one the chain carried into
    /// it -- a `From` conversion on the way out (design R8).
    pub translated: bool,
    /// Set on the LAST event of a chain, once the machine knows how it ended.
    pub terminal: Option<Terminal>,
    /// The type the chain was born with, for a record that has none of its own
    /// (design R4: an unbound arm's `type` comes from the chain it continues).
    pub origin_type: Option<String>,
}

/// Mint chain identity over one thread's ordered records.
///
/// `spawned` is "this is not the main thread": the only fact outside the
/// record stream the table needs, and the one that separates an `Err` left in
/// a `JoinHandle` from one that propagated.
#[must_use]
pub fn mint(records: &[Input], spawned: bool) -> Vec<ChainEvent> {
    let mut m = Machine::new(spawned);
    for input in records {
        if m.step(input) {
            break;
        }
    }
    m.finish();
    m.out
}

// ---------------------------------------------------------------------------
// The machine
// ---------------------------------------------------------------------------

/// A frame the simulation has open. `id` is minted, never a depth: a chain
/// remembers the frame it sits in, and two different frames at one depth must
/// never look like the same holder.
#[derive(Debug, Clone, Copy)]
struct Frame {
    id: u64,
    test: bool,
    main: bool,
    outermost: bool,
}

#[derive(Debug, Clone)]
struct Chain {
    serial: u64,
    /// The frame the chain currently sits in; `None` once it has left the
    /// outermost one.
    holder: Option<u64>,
    /// The marks of the frame it last sat in, kept because the frame itself is
    /// gone by the time the thread ends.
    last_frame: Frame,
    last: ErrText,
    origin: Origin,
    origin_type: Option<String>,
    hops: u32,
    /// A sink absorbed it; whether that reads as a swallow depends on how its
    /// holder closes.
    sink: bool,
    /// It shares a window with a different `Err` -- every member of a merged
    /// group ends as [`Terminal::Merged`].
    merged: bool,
    /// Index in `out` of this chain's most recent event: where the terminal
    /// goes when the chain ends.
    last_event: usize,
}

struct Machine {
    spawned: bool,
    stack: Vec<Frame>,
    next_frame_id: u64,
    next_serial: u64,
    /// Open chains, innermost last.
    chains: Vec<Chain>,
    out: Vec<ChainEvent>,
}

impl Machine {
    fn new(spawned: bool) -> Machine {
        Machine {
            spawned,
            stack: Vec::new(),
            next_frame_id: 0,
            next_serial: FIRST_CHAIN_SERIAL,
            chains: Vec::new(),
            out: Vec::new(),
        }
    }

    /// One record. Returns true when the thread has ended and the rest of the
    /// stream is not this thread's business.
    fn step(&mut self, input: &Input) -> bool {
        match &input.rec {
            Rec::Call { test, main } => {
                let id = self.next_frame_id;
                self.next_frame_id += 1;
                let outermost = self.stack.is_empty();
                self.stack.push(Frame {
                    id,
                    test: *test,
                    main: *main,
                    outermost,
                });
            }
            Rec::Return { outcome, text } => self.close_frame(input.seq, *outcome, text),
            Rec::ErrFlow { how, text } => self.err_flow(input.seq, *how, text),
            Rec::ThreadEnd => return true,
        }
        false
    }

    fn finish(&mut self) {
        while let Some(c) = self.chains.pop() {
            let terminal = if c.merged {
                Terminal::Merged
            } else {
                let f = c.last_frame;
                if f.test || f.main {
                    Terminal::ReturnedToHarness
                } else if self.spawned && f.outermost {
                    Terminal::LeftThread
                } else {
                    Terminal::Propagated
                }
            };
            self.out[c.last_event].terminal = Some(terminal);
        }
    }

    // -- rows -------------------------------------------------------------

    /// The four close rows of §2a, applied to every chain the closing frame
    /// holds (innermost first).
    fn close_frame(&mut self, seq: u64, outcome: Outcome, text: &ErrText) {
        let Some(frame) = self.stack.pop() else {
            // A RETURN with no open frame is a malformed stream, refused by
            // `frames.rs` with pid, thread and seq. Nothing to say here.
            return;
        };
        let parent = self.stack.last().map(|f| f.id);
        let mut consumed_err = false;
        let mut i = self.chains.len();
        while i > 0 {
            i -= 1;
            if self.chains[i].holder != Some(frame.id) {
                continue;
            }
            match outcome {
                Outcome::Panic => {
                    let c = self.chains.remove(i);
                    self.end(&c, Terminal::Panicked);
                }
                Outcome::Ok => {
                    let c = self.chains.remove(i);
                    let terminal = if c.merged {
                        Terminal::Merged
                    } else if c.sink {
                        Terminal::SwallowedCandidate
                    } else {
                        Terminal::AmbiguousEscaped
                    };
                    self.end(&c, terminal);
                }
                Outcome::Err | Outcome::None => {
                    if self.chains[i].merged {
                        continue;
                    }
                    if self.chains[i].sink {
                        let c = self.chains.remove(i);
                        self.end(&c, Terminal::HandledThenFailed);
                        continue;
                    }
                    if outcome == Outcome::Err && !consumed_err {
                        consumed_err = true;
                        self.hop_out(i, seq, &frame, parent, text);
                    } else {
                        // The `?` propagated: the hop was already recorded by
                        // the try RAISE, so the chain only changes hands.
                        self.chains[i].holder = parent;
                        self.chains[i].last_frame = frame;
                    }
                }
            }
        }
        if outcome == Outcome::Err && !consumed_err {
            self.open_at_exit(seq, &frame, parent, text);
        }
    }

    /// `F == H` on an `err` close: the frame re-returned the `Err` it held,
    /// possibly translated on the way out.
    fn hop_out(&mut self, i: usize, seq: u64, frame: &Frame, parent: Option<u64>, text: &ErrText) {
        let translated = !text.matches(&self.chains[i].last);
        self.chains[i].holder = parent;
        self.chains[i].last_frame = *frame;
        self.chains[i].hops += 1;
        self.chains[i].last = text.clone();
        let event = ChainEvent {
            seq,
            at: At::ExitBefore,
            serial: self.chains[i].serial,
            hop: self.chains[i].hops,
            origin: self.chains[i].origin,
            translated,
            terminal: None,
            origin_type: self.chains[i].origin_type.clone(),
        };
        self.chains[i].last_event = self.out.len();
        self.out.push(event);
    }

    /// A frame closing `err` while holding no chain of its own: the `Err` is
    /// born here, and the origin RAISE goes in front of the RETURN.
    fn open_at_exit(&mut self, seq: u64, frame: &Frame, parent: Option<u64>, text: &ErrText) {
        self.open_chain(seq, At::ExitBefore, parent, *frame, text, Origin::Workspace);
    }

    /// The RAISE and HANDLED rows.
    fn err_flow(&mut self, seq: u64, how: How, text: &ErrText) {
        let Some(&frame) = self.stack.last() else {
            // Counted as `err_flow_outside_frames` by `frames.rs` and written
            // as no event at all, so there is nothing for a chain to hold.
            return;
        };
        let held = self.chains.iter().rposition(|c| c.holder == Some(frame.id));
        match held {
            Some(i) if self.chains[i].merged => self.merged_row(i, seq, how, frame, text),
            Some(i) if how.is_raise() => {
                if text.matches(&self.chains[i].last) {
                    self.hop_in_place(i, seq, text);
                } else {
                    self.merge_with(i, seq, frame, text);
                }
            }
            Some(i) if text.matches(&self.chains[i].last) => {
                self.absorb(i, seq, how, text);
            }
            // A HANDLED whose text is a DIFFERENT `Err` from the one this
            // frame holds is not that chain's business: it behaves exactly as
            // it would in a frame holding nothing (§2a's `None` column).
            _ => self.chainless(seq, how, frame, text),
        }
    }

    /// The `Merged` column: a RAISE adds a serial to the group, a HANDLED
    /// behaves as it would with no chain, and everything else leaves the group
    /// as it is.
    fn merged_row(&mut self, i: usize, seq: u64, how: How, frame: Frame, text: &ErrText) {
        if how.is_raise() {
            let j = self.open_chain(
                seq,
                At::Record,
                Some(frame.id),
                frame,
                text,
                Origin::Workspace,
            );
            self.chains[j].merged = true;
        } else if how == How::ArmAmbiguous {
            // "stays": the record is reported against the group it landed in,
            // and changes nothing about it.
            self.record_event(i, seq, false);
        } else {
            self.chainless(seq, how, frame, text);
        }
    }

    /// `G == H` and the same `Err`: the `?` (or the propagating arm) on the
    /// value this frame already holds.
    fn hop_in_place(&mut self, i: usize, seq: u64, text: &ErrText) {
        self.chains[i].hops += 1;
        self.chains[i].last.learn_from(text);
        self.record_event(i, seq, false);
    }

    /// `G == H` and a DIFFERENT `Err`: two live errors in one frame's window,
    /// which is the shape design R8 refuses to call a swallow.
    fn merge_with(&mut self, i: usize, seq: u64, frame: Frame, text: &ErrText) {
        self.chains[i].merged = true;
        let j = self.open_chain(
            seq,
            At::Record,
            Some(frame.id),
            frame,
            text,
            Origin::Workspace,
        );
        self.chains[j].merged = true;
    }

    /// A HANDLED-class record against the chain its frame holds.
    fn absorb(&mut self, i: usize, seq: u64, how: How, text: &ErrText) {
        self.chains[i].last.learn_from(text);
        if how == How::ArmAmbiguous {
            self.record_event(i, seq, false);
            let c = self.chains.remove(i);
            self.end(&c, Terminal::AmbiguousEscaped);
            return;
        }
        if how.is_sink() {
            self.chains[i].sink = true;
        }
        self.record_event(i, seq, false);
    }

    /// §2a's `None` column for a HANDLED: a chain that opens and closes around
    /// one absorbed `Err` whose origin this recording never saw.
    fn chainless(&mut self, seq: u64, how: How, frame: Frame, text: &ErrText) {
        let j = self.open_chain(
            seq,
            At::Record,
            Some(frame.id),
            frame,
            text,
            Origin::Outside,
        );
        self.chains[j].sink = how.is_sink();
        if how == How::ArmAmbiguous {
            let c = self.chains.remove(j);
            self.end(&c, Terminal::AmbiguousEscaped);
        }
    }

    // -- helpers ----------------------------------------------------------

    /// Open a chain and push the event it is born AT -- the one place a serial
    /// is minted, so a chain and its first event can never disagree about
    /// which chain they are. Returns the new chain's index.
    fn open_chain(
        &mut self,
        seq: u64,
        at: At,
        holder: Option<u64>,
        frame: Frame,
        text: &ErrText,
        origin: Origin,
    ) -> usize {
        let serial = self.next_serial;
        self.next_serial += 1;
        let origin_type = text.type_name.clone();
        self.out.push(ChainEvent {
            seq,
            at,
            serial,
            hop: 1,
            origin,
            translated: false,
            terminal: None,
            origin_type: origin_type.clone(),
        });
        self.chains.push(Chain {
            serial,
            holder,
            last_frame: frame,
            last: text.clone(),
            origin,
            origin_type,
            hops: 1,
            sink: false,
            merged: false,
            last_event: self.out.len() - 1,
        });
        self.chains.len() - 1
    }

    /// An event on an existing chain, at the hop it currently sits at.
    fn record_event(&mut self, i: usize, seq: u64, translated: bool) {
        let event = ChainEvent {
            seq,
            at: At::Record,
            serial: self.chains[i].serial,
            hop: self.chains[i].hops,
            origin: self.chains[i].origin,
            translated,
            terminal: None,
            origin_type: self.chains[i].origin_type.clone(),
        };
        self.chains[i].last_event = self.out.len();
        self.out.push(event);
    }

    fn end(&mut self, c: &Chain, terminal: Terminal) {
        self.out[c.last_event].terminal = Some(terminal);
    }
}

#[cfg(test)]
mod tests;
