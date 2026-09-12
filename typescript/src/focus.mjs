// Which functions a `--focus` spec selects. One rule, asked at three moments:
// by the resolver before the run (Task 5), by the transform while it splices
// (Task 4), and by the reader's `--at` in Python (Task 7) — which is a SECOND
// implementation of this file, pinned to it by one example table
// (`../test/fixtures/site-spellings.json`), because a spelling a reader cannot
// repeat is a spelling the recorder should not have accepted (spec §4.3).
//
// A spec is `<qualname>` or `<file>:<qualname>` (spec §2.1). The qualname is
// what `tree` prints — `Fog.compute`, `outer.inner`, `refresh`, `default` — and
// a value naming a CONTAINER selects everything under it on a `.` boundary,
// which is the only way to name an anonymous function (`<anonymous>` carries no
// ordinal, and `<` is the shell's). The file part narrows and is optional. No
// globs, no regexes, no line numbers.
//
// No state and no I/O: strings in, verdicts out.
import path from 'node:path';

/** @typedef {{file: string|null, qualname: string}} Spec */

/**
 * The unit separator, written as an escape so no editor strips it. The driver
 * joins the specs with it into one `SENSORIUM_FOCUS` variable, because a spec
 * may hold a path, a dot and a colon, and this is the one byte it cannot.
 */
export const SEP = '\x1f';

/**
 * The specs an environment value carries. An empty value is no focus at all,
 * and an empty FIELD is dropped rather than kept: `''` as a spec would have an
 * empty qualname, and `qualnameMatches` would then select every function in
 * the root — the one mistake that turns a focus into a whole-program recording.
 * @param {string} value
 * @returns {string[]}
 */
export function specsFromEnv(value) {
  return value.split(SEP).filter((spec) => spec !== '');
}

/**
 * A spec's two parts, split at the FIRST colon: a Windows drive letter is not a
 * spelling here, and a later colon belongs to the qualname it appears in.
 * @param {string} spec
 * @returns {Spec}
 */
export function parseSpec(spec) {
  const cut = spec.indexOf(':');
  if (cut === -1) return { file: null, qualname: spec };
  return { file: spec.slice(0, cut), qualname: spec.slice(cut + 1) };
}

/**
 * Whether a function's qualname is selected by a spec's qualname part: the name
 * itself, or a container of it on a `.` boundary. `Fog` selects `Fog.compute`;
 * `Fog` does not select `Fogs.compute`, and `compute` selects neither — this is
 * a prefix rule, so a member is reached by naming its container, never by
 * naming the member alone.
 * @param {string} qualname
 * @param {string} want
 * @returns {boolean}
 */
export function qualnameMatches(qualname, want) {
  return qualname === want || qualname.startsWith(`${want}.`);
}

/**
 * Whether a root-relative path is selected by a spec's file part: the path
 * itself (`src/lib/cache.ts`), the basename (`cache.ts`), or the stem
 * (`cache`, the basename without its LAST extension). A directory segment is
 * not a spelling, and neither is part of a path.
 * @param {string} rel root-relative, in the platform's own separators
 * @param {string} want
 * @returns {boolean}
 */
export function fileMatches(rel, want) {
  if (rel === want) return true;
  const base = path.basename(rel);
  if (base === want) return true;
  const ext = path.extname(base);
  return ext !== '' && base.slice(0, -ext.length) === want;
}

/**
 * Whether a spec selects the function at `rel` named `qualname`. The file part
 * only ever NARROWS: a spec without one selects every matching qualname under
 * the root, which is what a bare `--focus load` means and what `focus_matched`
 * then lists.
 * @param {string} spec
 * @param {string} rel
 * @param {string} qualname
 * @returns {boolean}
 */
export function specMatches(spec, rel, qualname) {
  const { file, qualname: want } = parseSpec(spec);
  if (file !== null && !fileMatches(rel, file)) return false;
  return qualnameMatches(qualname, want);
}

/**
 * @param {string[]} parts
 * @param {string[]} want
 * @returns {number} how many WHOLE trailing segments the two share
 */
function sharedTail(parts, want) {
  let shared = 0;
  while (
    shared < parts.length &&
    shared < want.length &&
    parts[parts.length - 1 - shared] === want[want.length - 1 - shared]
  ) {
    shared += 1;
  }
  return shared;
}

/**
 * The suggestions a refusal names: the eligible qualnames sharing the longest
 * trailing run of `.`-separated segments with the spec's qualname part, most
 * first, ties by name. A candidate sharing NOTHING is still a suggestion — the
 * clause is dropped only when the root holds no eligible function at all (spec
 * §2.2), because a reader who mistyped the container needs the list most.
 * @param {string[]} eligible every qualname the root offers
 * @param {string} want the spec's qualname part, after `parseSpec`
 * @param {number} [limit]
 * @returns {string[]} at most `limit` names
 */
export function closest(eligible, want, limit = 3) {
  const parts = want.split('.');
  const scored = eligible.map((name) => ({ name, shared: sharedTail(name.split('.'), parts) }));
  scored.sort((a, b) => {
    if (a.shared !== b.shared) return b.shared - a.shared;
    if (a.name === b.name) return 0;
    return a.name < b.name ? -1 : 1;
  });
  return scored.slice(0, limit).map((entry) => entry.name);
}
