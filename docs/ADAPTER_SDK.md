# AlphaSource Adapter SDK — Developer Guide

**Sprint 13 deliverable.** Infrastructure, not integrations: this sprint
adds zero site-specific scraping logic. It replaces Sprint 12's ad-hoc,
extension-only adapter list with a standalone, testable SDK
(`adapter-sdk/`) that any future data source — a specific website, a file
format, a spreadsheet export — plugs into without anyone touching the
extension's core files. Nothing in the Sprint 12 backend (`/candidate/import`,
`CandidateRepository`, dedup/merge) changed; this SDK produces the exact
same candidate shape that endpoint already accepts.

## 1. Why this exists

Sprint 12 proved recruiter-authorized capture works. But its extraction
logic lived directly inside the browser extension, as a small, hand-rolled
adapter registry with two hardcoded adapters. Supporting "hundreds of data
sources" that way would mean every new source touching
`background/service-worker.js`. This SDK fixes that: adapters are now a
standalone package with a formal lifecycle contract, a test harness, a
benchmark harness, and a debug overlay — and the extension only ever reads
a generated manifest, never a hardcoded file list.

**Goal, stated plainly: a new adapter should be addable in under a day,
without modifying `extension/background/service-worker.js`,
`extension/popup/popup.js`, `extension/content-scripts/extractor.js`, or
any backend file.**

## 2. The lifecycle contract

Every adapter is a plain object built by `defineAdapter()`
(`adapter-sdk/core/base-adapter.js`):

```js
const { defineAdapter } = require("./_sdk-import")("base-adapter");

module.exports.myAdapter = defineAdapter({
  name: "my-adapter",       // required, unique
  priority: 0,              // optional, default 0 -- higher runs first
  inputKinds: ["dom"],      // optional, default ["dom"] -- dom | text | row

  detect(input) {           // required
    // Return a confidence number in (0, 1], `true` (treated as 1), or a
    // falsy value if this adapter doesn't recognize the input.
  },

  extract(input) {          // required
    // Return a plain object (or, for a "multi" adapter, an array of plain
    // objects) of whatever raw fields this source naturally exposes.
  },

  normalize(raw, input) {   // optional -- defaults to identity
    // Map `raw` onto the canonical candidate shape (see
    // core/candidate-schema.js's CANDIDATE_FIELDS): name, role, headline,
    // current_company, experience_years, skills, location, summary,
    // education, public_profile_url, resume_link.
  },

  validate(fields) {        // optional -- defaults to schema validation
    // Return { valid, errors[] }. Override only to add domain-specific
    // rules on top of the default type/required-field check.
  },

  locateElements(input) {   // optional, dom adapters only -- defaults to []
    // Return the DOM elements this adapter actually read from, purely for
    // the visual debug overlay (see §6). Has zero effect on extraction.
  },
});
```

Only `name`, `detect`, and `extract` are required — everything else has a
sane default. Every adapter file ends with the same two-line export block
(see any file in `adapter-sdk/adapters/` for the exact pattern) so it works
both as a Node `require()` (tests/benchmarks) and as a plain
`<script>`/`executeScript` file in a browser content-script context
(where it attaches itself to `window.__AlphaSourceSDK.adapters`).

## 3. SourceInput: the one abstraction across DOM / text / row

`adapter-sdk/core/source-input.js` is what lets the same registry run a
webpage adapter, a pasted-resume-text adapter, and a CSV-row adapter
through one pipeline:

| kind | payload | used by |
|---|---|---|
| `"dom"` | a `Document` (real or jsdom) | generic-html, json-ld, career-page-listing |
| `"text"` | a plain string | resume-text |
| `"row"` | a plain key/value object (one already-parsed record) | csv-row |

The SDK does not ship a CSV *parser* — splitting raw CSV text into rows is
a solved, generic problem handled upstream by whatever loads the file.
`csv-row.js` only maps one row's arbitrary column names onto the canonical
schema via a flexible alias table (`FIELD_ALIASES`).

## 4. The registry: automatic adapter selection

`adapter-sdk/core/registry.js`'s `AdapterRegistry.runPipeline(input)`:

1. Filters to adapters whose `inputKinds` includes the input's kind.
2. Calls `detect()` on each (in priority order), catching any thrown error
   so one broken adapter never blocks the others.
3. Picks the highest-confidence match.
4. Runs `extract → normalize → validate` on the winner only.
5. Returns `{ matched, adapterUsed, confidence, fields, valid, errors,
   trace, timings }` — `trace` has every adapter's attempt (used by the
   debug overlay and the benchmark harness), `fields` is a single object
   or (for a "multi" adapter like career-page-listing) an array.

There is no manual "if url contains X" dispatch anywhere — adding a new,
more specific adapter with a higher `priority` is the entire mechanism for
making it win over a generic fallback.

## 5. The five example adapters

| Adapter | Input | What it demonstrates |
|---|---|---|
| `generic-html` | dom | Fallback DOM/meta-tag heuristics — the lowest-priority safety net |
| `json-ld` | dom | Structured schema.org `Person` JSON-LD parsing — higher confidence than heuristics |
| `resume-text` | text | Freeform text parsing (email/phone/section-header regexes) |
| `csv-row` | row | Flexible column-name-alias mapping, no CSV parser included |
| `career-page-listing` | dom | A **multi** adapter — one page, many candidates, array output |

None of these contain a single hardcoded reference to a real company or
platform's markup — see docs/BROWSER_EXTENSION_ARCHITECTURE.md §8 for why
that's a hard constraint, not a style choice.

## 6. Writing a new adapter, end to end (the "under a day" workflow)

1. **Write the adapter.** Copy the shape from any file in
   `adapter-sdk/adapters/`. Put your file in `adapter-sdk/adapters/`.
2. **Write a fixture.** Create `adapter-sdk/testing/fixtures/<your-adapter>/`
   with an `input.html` / `input.txt` / `input.json`, an optional
   `meta.json` (`{ "url": "..." }`), and an `expected.json`
   (`{ adapterUsed, fields }` — `fields` is checked as a **partial**
   match, so you only need to assert what your adapter is responsible
   for).
3. **Run the tests:** `cd adapter-sdk && npm install && npm test`. Add
   your adapter's `require()` to `testing/run-tests.js`'s
   `buildRegistry()` (the one line of registry wiring every fixture-based
   test needs).
4. **Run the benchmark:** `npm run benchmark` — confirms your adapter's
   `detect()`/`extract()` stay under the latency budget (5ms/15ms p95 by
   default; see `testing/benchmark.js`).
5. **Regenerate the extension's copy:**
   `node scripts/sync-adapter-sdk-to-extension.js` from the repo root.
   This regenerates `adapter-sdk/manifest.json` (via `build-manifest.js`)
   and copies every core/adapter/debug file into
   `extension/vendor/adapter-sdk/`. **This is the entire integration
   step** — `extension/background/service-worker.js` reads the manifest
   at runtime, so it never needs to change.
6. **Verify visually (optional):** load the extension, open a real page
   your adapter should match, click "Debug this page" in the popup (see
   §7) to see every adapter's confidence and the winning one's matched
   elements highlighted.

No step above touches `background/service-worker.js`, `popup.js`,
`extractor.js`, or any backend file.

## 7. Testing framework

`adapter-sdk/testing/run-tests.js` (`npm test`): loads every fixture,
determines the `SourceInput` kind from which `input.*` file is present,
runs the real registry pipeline (jsdom for `input.html` fixtures), and
partially matches the result against `expected.json`. Exits non-zero on
any failure — safe to wire into CI.

```
$ cd adapter-sdk && npm test
PASS  career-page-listing
PASS  csv-row
PASS  generic-html
PASS  json-ld
PASS  resume-text

5/5 fixtures passed.
```

## 8. Visual debug mode

`adapter-sdk/debug/inspector.js` + `inspector.css`: an on-page floating
panel (bottom-right) showing every registered adapter's `detect()`
attempt — matched/confidence/timing/error — with the winner highlighted,
the final extracted+normalized fields as JSON, and (if the winning adapter
implements the optional `locateElements()` hook) the actual DOM elements
it read from outlined in cyan on the page.

In the extension: click the popup's **"Debug this page"** footer link.
Standalone (for adapter development against jsdom or a live page in
devtools): load `core/*.js`, `adapters/*.js`, and `debug/inspector.js` +
`inspector.css`, then call `window.__AlphaSourceDebugInspector.run()`.

## 9. Performance benchmarking

`adapter-sdk/testing/benchmark.js` (`npm run benchmark [iterations]`):
runs each fixture's adapter through `detect()`/`extract()` N times
(default 200) and reports avg/p95 latency against a budget (detect p95 ≤
5ms, extract p95 ≤ 15ms by default). A result over budget exits non-zero,
so a pathological new adapter (e.g. an accidental O(n²) DOM walk) is
caught before it ships, not after a recruiter complains the popup is
slow.

```
adapter               detect avg   detect p95   extract avg   extract p95   status
career-page-listing   0.822ms      2.067ms      1.009ms       2.593ms       OK
csv-row               0.006ms      0.003ms      0.029ms       0.039ms       OK
generic-html          0.112ms      0.292ms      1.144ms       3.959ms       OK
json-ld-person        0.146ms      0.395ms      0.189ms       0.533ms       OK
resume-text           0.005ms      0.004ms      0.042ms       0.084ms       OK
```

A snapshot of the most recent run is kept at
`adapter-sdk/testing/reports/benchmark-latest.txt` for reference; it is
not regenerated automatically and will drift from the live numbers over
time — re-run `npm run benchmark` for current figures.

## 10. Manifest-driven extension loading

`adapter-sdk/build-manifest.js` generates `adapter-sdk/manifest.json`: an
ordered list of every core + adapter file, computed by scanning
`adapter-sdk/adapters/` (core files are hardcoded in the required
dependency order; adapter files are auto-discovered). `extension/
background/service-worker.js` fetches this manifest (vendored alongside
the files themselves in `extension/vendor/adapter-sdk/`) at runtime and
injects exactly those files via `chrome.scripting.executeScript` before
running extraction, capture, or debug — it contains no adapter file names
itself.

## 11. Known limitations (Proof of Concept)

- The vendored copy under `extension/vendor/adapter-sdk/` must be
  regenerated manually (`node scripts/sync-adapter-sdk-to-extension.js`)
  after any adapter-sdk change — there is no file-watcher or build step
  wired into a larger build system yet.
- `scripts/sync-adapter-sdk-to-extension.js` overwrites files in place
  rather than deleting-then-recopying, because this project's current
  filesystem does not permit deleting files once written. A file removed
  from `adapter-sdk/` will not be automatically removed from the vendored
  copy — harmless today, since `manifest.json` (not directory contents)
  controls what gets injected, but worth fixing with real `fs.rm` access.
- `career-page-listing`'s structural heuristic (repeated name-shaped
  headings) is deliberately simple and will both miss some real team pages
  and occasionally over-match on pages with many proper-noun headings that
  aren't people (e.g. a blog's list of city names). Treat it as a starting
  point for a real adapter, not a finished one.
- The debug overlay's element highlighting only works for adapters that
  implement `locateElements()`; `json-ld`, `resume-text`, and `csv-row`
  don't (there's no natural DOM element to highlight for a JSON-LD script
  tag, freeform text, or a spreadsheet row), so the overlay shows their
  extracted fields without highlighting when they win.
