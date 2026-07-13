/**
 * Tiny shared helper so every adapter file can do
 * `const { defineAdapter } = require("./_sdk-import")("base-adapter");`
 * in Node/tests, or rely on window.__AlphaSourceSDK in a browser
 * content-script context, without repeating the require/window branch in
 * every single adapter file. Not part of the public SDK surface -- just
 * plumbing.
 */
function loadSdkModule(moduleName) {
  if (typeof require !== "undefined") {
    try {
      return require(`../core/${moduleName}`);
    } catch (e) {
      // fall through to the browser global below
    }
  }
  if (typeof window !== "undefined" && window.__AlphaSourceSDK) {
    const key = moduleName
      .replace(/-([a-z])/g, (_, c) => c.toUpperCase())
      .replace(/^base-adapter$/, "defineAdapter");
    if (moduleName === "base-adapter") return { defineAdapter: window.__AlphaSourceSDK.defineAdapter };
    if (moduleName === "candidate-schema") return window.__AlphaSourceSDK.candidateSchema;
    if (moduleName === "source-input") return { SourceInput: window.__AlphaSourceSDK.SourceInput };
    if (moduleName === "registry") return { AdapterRegistry: window.__AlphaSourceSDK.AdapterRegistry };
  }
  throw new Error(`_sdk-import: could not resolve "${moduleName}" -- is the core SDK loaded first?`);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = loadSdkModule;
}
if (typeof window !== "undefined") {
  window.__AlphaSourceLoadSdkModule = loadSdkModule;
}
