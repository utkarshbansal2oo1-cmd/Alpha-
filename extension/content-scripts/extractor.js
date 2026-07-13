/**
 * Extraction entry point (Sprint 13 rewrite) -- generic over whatever
 * adapters happen to be loaded via vendor/adapter-sdk/manifest.json. This
 * file has ZERO knowledge of how many adapters exist or what they're
 * called: it builds an AdapterRegistry, registers every adapter the SDK
 * files attached to window.__AlphaSourceSDK.adapters, and runs the
 * pipeline. Adding a new adapter to adapter-sdk/adapters/ and re-running
 * scripts/sync-adapter-sdk-to-extension.js is the entire integration --
 * this file never needs to change.
 *
 * Returns one of:
 *   { detected: false }
 *   { detected: true, multi: false, adapterUsed, confidence, fields, valid, errors }
 *   { detected: true, multi: true,  adapterUsed, confidence, fields: [...], valid, errors }
 */
window.__alphaSourceExtractCandidate = function () {
  const sdk = window.__AlphaSourceSDK || {};
  const registry = new sdk.AdapterRegistry();

  Object.values(sdk.adapters || {}).forEach((adapter) => registry.register(adapter));

  const input = sdk.SourceInput.fromDocument(document, { url: document.location.href });
  const result = registry.runPipeline(input);

  if (!result.matched) {
    return { detected: false };
  }

  return {
    detected: true,
    multi: Array.isArray(result.fields),
    adapterUsed: result.adapterUsed,
    confidence: result.confidence,
    fields: result.fields,
    valid: result.valid,
    errors: result.errors,
  };
};
