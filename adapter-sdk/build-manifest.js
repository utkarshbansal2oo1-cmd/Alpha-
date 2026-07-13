#!/usr/bin/env node
/**
 * Generates a load-order manifest for every core + adapter file in this
 * SDK, and writes it as manifest.json. Any consumer that needs to inject
 * these files as plain <script>/executeScript files (like the browser
 * extension) reads this manifest instead of hardcoding a file list --
 * so adding a new file under adapters/ and re-running this script is the
 * *entire* integration step, with zero edits to the extension's own code.
 *
 * Load order: core files first, in the order they depend on each other
 * (source-input/candidate-schema have no deps -> base-adapter depends on
 * candidate-schema -> registry depends on nothing else), then the
 * "_sdk-import" plumbing helper, then every adapter file (each of which
 * self-registers onto window.__AlphaSourceSDK.adapters when loaded as a
 * plain script -- see any adapters/*.js file's bottom `if (window...)`
 * block).
 *
 * Usage: `node adapter-sdk/build-manifest.js` from the repo root or from
 * inside adapter-sdk/. Re-run this after adding/removing an adapter file.
 */
const fs = require("fs");
const path = require("path");

const SDK_ROOT = __dirname;
const CORE_ORDER = ["source-input.js", "candidate-schema.js", "base-adapter.js", "registry.js"];

function listAdapterFiles() {
  const adaptersDir = path.join(SDK_ROOT, "adapters");
  return fs
    .readdirSync(adaptersDir)
    .filter((f) => f.endsWith(".js") && f !== "_sdk-import.js")
    .sort();
}

function buildManifest() {
  const core = CORE_ORDER.map((f) => `core/${f}`);
  const helper = ["adapters/_sdk-import.js"];
  const adapters = listAdapterFiles().map((f) => `adapters/${f}`);

  return {
    generatedAt: new Date().toISOString(),
    description:
      "Load order for the Adapter SDK's core + adapter files. Consumers (e.g. the browser extension) should inject these files, in this exact order, before running the extraction pipeline.",
    files: [...core, ...helper, ...adapters],
  };
}

if (require.main === module) {
  const manifest = buildManifest();
  const outPath = path.join(SDK_ROOT, "manifest.json");
  fs.writeFileSync(outPath, JSON.stringify(manifest, null, 2) + "\n");
  console.log(`Wrote ${outPath} with ${manifest.files.length} files:`);
  manifest.files.forEach((f) => console.log(`  - ${f}`));
}

module.exports = { buildManifest };
