/**
 * AdapterRegistry -- automatic adapter selection + the detect -> extract ->
 * normalize -> validate pipeline. This is the entire "core" of the
 * Adapter SDK; every adapter (built-in or third-party) is just a plain
 * object built by defineAdapter() (base-adapter.js) that gets register()ed
 * here. Nothing in this file knows about any specific site, file format,
 * or data source -- see docs/ADAPTER_SDK.md.
 *
 * Selection algorithm (runPipeline):
 *   1. Filter to adapters whose `inputKinds` includes the input's kind.
 *   2. Call detect(input) on each, in `priority` order (highest first;
 *      ties broken by registration order). detect() may return:
 *        - a number in (0, 1]  -> treated as a confidence score
 *        - `true`              -> treated as confidence 1
 *        - anything falsy      -> not matched
 *      A thrown error from one adapter's detect() is caught and recorded
 *      as a failed attempt -- it never blocks the others from being tried
 *      (the same "one bad adapter can't break the page" principle from
 *      Sprint 12's extractor.js).
 *   3. The highest-confidence match wins. If nothing matches, the result
 *      is `{ matched: false }` and the caller (e.g. the extension popup)
 *      should fall back to "no candidate detected" -- there is always a
 *      generic fallback adapter registered at low priority so, in
 *      practice, `matched: false` should only happen for genuinely
 *      unrelated content (see adapters/generic-html.js).
 *   4. extract() -> normalize() -> validate() run only on the winning
 *      adapter. If validate() reports invalid, the result still comes back
 *      (matched: true, valid: false, errors) rather than silently
 *      discarded -- callers decide what to do with an invalid extraction
 *      (e.g. the popup can show a warning but still let the recruiter
 *      manually review/edit before submitting).
 *
 * `runPipeline`'s returned `trace` array is exactly what the visual debug
 * mode (adapter-sdk/debug/inspector.js) and the benchmarking harness
 * (adapter-sdk/testing/benchmark.js) both consume -- one instrumentation
 * point serves both features.
 */
class AdapterRegistry {
  constructor() {
    this._adapters = [];
  }

  register(adapter) {
    if (!adapter || typeof adapter.detect !== "function" || typeof adapter.extract !== "function") {
      throw new Error("AdapterRegistry.register: not a valid adapter (use defineAdapter())");
    }
    this._adapters.push(adapter);
    return this;
  }

  list() {
    return [...this._adapters].sort((a, b) => b.priority - a.priority);
  }

  /** Runs detect() on every eligible adapter and returns the full trace,
   * without running extract/normalize/validate. Used standalone by the
   * visual debug mode to show every adapter's attempt, not just the
   * winner. */
  detectAll(input) {
    const eligible = this.list().filter((a) => a.inputKinds.includes(input.kind));
    const trace = [];

    for (const adapter of eligible) {
      const startedAt = _now();
      try {
        const raw = adapter.detect(input);
        const confidence = _normalizeConfidence(raw);
        trace.push({
          adapter: adapter.name,
          priority: adapter.priority,
          matched: confidence > 0,
          confidence,
          error: null,
          detectMs: _now() - startedAt,
        });
      } catch (e) {
        trace.push({
          adapter: adapter.name,
          priority: adapter.priority,
          matched: false,
          confidence: 0,
          error: String(e?.message || e),
          detectMs: _now() - startedAt,
        });
      }
    }

    return trace;
  }

  /** Full pipeline: select the best adapter, then extract/normalize/validate
   * with it. Returns { matched, adapterUsed, confidence, fields, valid,
   * errors, trace, timings }. */
  runPipeline(input) {
    const detectTrace = this.detectAll(input);
    const best = detectTrace
      .filter((t) => t.matched)
      .sort((a, b) => b.confidence - a.confidence)[0];

    if (!best) {
      return {
        matched: false,
        adapterUsed: null,
        confidence: 0,
        fields: null,
        valid: false,
        errors: ["No adapter matched this input"],
        trace: detectTrace,
        timings: { extractMs: 0, normalizeMs: 0, validateMs: 0 },
      };
    }

    const adapter = this._adapters.find((a) => a.name === best.adapter);

    const extractStart = _now();
    const raw = adapter.extract(input);
    const extractMs = _now() - extractStart;

    const normalizeStart = _now();
    const fields = adapter.normalize(raw, input);
    const normalizeMs = _now() - normalizeStart;

    const validateStart = _now();
    const { valid, errors } = adapter.validate(fields);
    const validateMs = _now() - validateStart;

    return {
      matched: true,
      adapterUsed: adapter.name,
      confidence: best.confidence,
      fields,
      valid,
      errors,
      trace: detectTrace,
      timings: { extractMs, normalizeMs, validateMs },
    };
  }
}

function _normalizeConfidence(raw) {
  if (raw === true) return 1;
  if (typeof raw === "number") return Math.max(0, Math.min(1, raw));
  return 0;
}

function _now() {
  if (typeof performance !== "undefined" && performance.now) return performance.now();
  return Date.now();
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { AdapterRegistry };
}
if (typeof window !== "undefined") {
  window.__AlphaSourceSDK = Object.assign(window.__AlphaSourceSDK || {}, { AdapterRegistry });
}
