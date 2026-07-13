/**
 * SourceInput -- the one abstraction every adapter's detect()/extract()
 * receives, regardless of where the raw data came from. This is what lets
 * the SAME registry/pipeline run a DOM-based adapter (a webpage), a
 * text-based adapter (a pasted resume), or a row-based adapter (one CSV
 * record) without the core framework caring which.
 *
 * kind: "dom"   -> payload is a Document (or Document-like object -- a real
 *                  `document` in a browser/content-script context, or a
 *                  jsdom Document in tests/Node).
 * kind: "text"  -> payload is a plain string (e.g. resume text pasted by a
 *                  recruiter, or text extracted upstream from a .txt/.docx).
 * kind: "row"   -> payload is a plain object of already-parsed key/value
 *                  pairs (e.g. one row of a CSV, already split into
 *                  columns by whatever loaded the file -- this SDK does not
 *                  ship a CSV *parser*, only a CSV *row normalizer*, since
 *                  parsing CSV text into rows is a solved, generic problem
 *                  that doesn't belong in an adapter).
 *
 * `meta` carries provenance that isn't part of the candidate data itself
 * (e.g. the page URL for a dom input, or a filename for a row/text input) --
 * adapters may read it but the framework never requires it.
 *
 * Loadable two ways: `require("./source-input")` in Node/tests, or as a
 * plain <script>/executeScript file in a browser content-script context,
 * where it attaches itself to `window.__AlphaSourceSDK.SourceInput`.
 */
class SourceInput {
  constructor(kind, payload, meta = {}) {
    if (!["dom", "text", "row"].includes(kind)) {
      throw new Error(`SourceInput: unknown kind "${kind}" (expected dom|text|row)`);
    }
    this.kind = kind;
    this.payload = payload;
    this.meta = meta;
  }

  static fromDocument(document, meta = {}) {
    return new SourceInput("dom", document, meta);
  }

  static fromText(text, meta = {}) {
    return new SourceInput("text", text, meta);
  }

  static fromRow(row, meta = {}) {
    return new SourceInput("row", row, meta);
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { SourceInput };
}
if (typeof window !== "undefined") {
  window.__AlphaSourceSDK = Object.assign(window.__AlphaSourceSDK || {}, { SourceInput });
}
