/**
 * defineAdapter() -- the one function every adapter (built-in or
 * third-party) uses to declare itself. This is the whole SDK contract:
 *
 *   detect(input)    -> boolean | number (0..1 confidence) | falsy
 *   extract(input)   -> a plain object of raw, adapter-specific fields
 *   normalize(raw, input) -> a plain object matching CANDIDATE_FIELDS
 *                            (candidate-schema.js) -- defaults to identity
 *                            (assumes extract() already returned the
 *                            canonical shape) if omitted
 *   validate(fields) -> {valid, errors[]} -- defaults to
 *                        validateCandidateFields() if omitted
 *   locateElements(input) -> DOM elements the extraction relied on
 *                            (optional, dom-input adapters only) --
 *                            defaults to []. Used exclusively by the
 *                            visual debug mode (debug/inspector.js) to
 *                            highlight what was matched on the page; has
 *                            no effect on extraction/normalization.
 *
 * Only `name`, `detect`, and `extract` are required. Everything else has a
 * sane default so a minimal new adapter is genuinely small -- see
 * docs/ADAPTER_SDK.md for a full walkthrough of writing one from scratch.
 */
function _resolveCandidateSchema() {
  if (typeof require !== "undefined") {
    try {
      return require("./candidate-schema");
    } catch (e) {
      // fall through to the browser global below
    }
  }
  if (typeof window !== "undefined" && window.__AlphaSourceSDK?.candidateSchema) {
    return window.__AlphaSourceSDK.candidateSchema;
  }
  throw new Error("base-adapter.js: candidate-schema.js must be loaded first");
}

const { validateCandidateFields } = _resolveCandidateSchema();

function defineAdapter(spec) {
  if (!spec || typeof spec !== "object") {
    throw new Error("defineAdapter: expected a spec object");
  }
  const { name, detect, extract } = spec;
  if (!name || typeof name !== "string") {
    throw new Error("defineAdapter: adapter must have a string `name`");
  }
  if (typeof detect !== "function") {
    throw new Error(`defineAdapter("${name}"): missing detect(input)`);
  }
  if (typeof extract !== "function") {
    throw new Error(`defineAdapter("${name}"): missing extract(input)`);
  }

  return {
    name,
    // Higher priority runs first when multiple adapters could match the
    // same input -- lets a specific adapter register ahead of a generic
    // fallback. Defaults to 0; the two ship-with-the-SDK generic adapters
    // should stay at or below 0.
    priority: typeof spec.priority === "number" ? spec.priority : 0,
    inputKinds: spec.inputKinds || ["dom"],
    detect,
    extract,
    normalize: typeof spec.normalize === "function" ? spec.normalize : (raw) => raw,
    validate: typeof spec.validate === "function" ? spec.validate : validateCandidateFields,
    locateElements: typeof spec.locateElements === "function" ? spec.locateElements : () => [],
  };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { defineAdapter };
}
if (typeof window !== "undefined") {
  window.__AlphaSourceSDK = Object.assign(window.__AlphaSourceSDK || {}, { defineAdapter });
}
