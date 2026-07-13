#!/usr/bin/env node
/**
 * Copies the Adapter SDK's core + adapter + debug files, plus its
 * generated manifest.json, into extension/vendor/adapter-sdk/. Chrome
 * extensions can only load files that live inside their own packed
 * directory, so the SDK (a standalone, testable package at the repo root)
 * needs a physical copy inside extension/ to be usable by
 * chrome.scripting.executeScript.
 *
 * This script is the ONLY thing that needs to run after adding a new
 * adapter to adapter-sdk/adapters/ -- it re-runs build-manifest.js and
 * re-copies files. Nothing in extension/background/service-worker.js or
 * extension/popup/popup.js needs to change, because the service worker
 * reads vendor/adapter-sdk/manifest.json at runtime instead of hardcoding
 * a file list.
 *
 * Usage: `node scripts/sync-adapter-sdk-to-extension.js` from the repo
 * root.
 */
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const REPO_ROOT = path.join(__dirname, "..");
const SDK_ROOT = path.join(REPO_ROOT, "adapter-sdk");
const VENDOR_ROOT = path.join(REPO_ROOT, "extension", "vendor", "adapter-sdk");

function copyDir(src, dest, opts = {}) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    if (entry.name.startsWith("_") && entry.name !== "_sdk-import.js") continue;
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      if ((opts.skipDirs || []).includes(entry.name)) continue;
      copyDir(srcPath, destPath, opts);
    } else if (entry.name.endsWith(".js") || entry.name.endsWith(".css")) {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function main() {
  console.log("Regenerating adapter-sdk/manifest.json...");
  execSync(`node "${path.join(SDK_ROOT, "build-manifest.js")}"`, { stdio: "inherit" });

  console.log(`Copying core/, adapters/, and debug/ into ${VENDOR_ROOT} ...`);
  // Overwrite in place rather than rm -rf + recopy: this repo runs on a
  // mounted filesystem that does not permit deleting files once written,
  // only overwriting them. copyFileSync overwrites existing files fine;
  // this just means a file REMOVED from adapter-sdk/ won't be removed
  // from the vendor copy automatically -- harmless, since manifest.json
  // (not directory contents) controls what actually gets injected for
  // extraction. Debug files are vendored separately (see
  // background/service-worker.js's "debug" message handler) since they're
  // not part of the extraction manifest.
  copyDir(path.join(SDK_ROOT, "core"), path.join(VENDOR_ROOT, "core"), { skipDirs: [] });
  copyDir(path.join(SDK_ROOT, "adapters"), path.join(VENDOR_ROOT, "adapters"), { skipDirs: [] });
  copyDir(path.join(SDK_ROOT, "debug"), path.join(VENDOR_ROOT, "debug"), { skipDirs: [] });

  fs.copyFileSync(
    path.join(SDK_ROOT, "manifest.json"),
    path.join(VENDOR_ROOT, "manifest.json")
  );

  console.log("Done. extension/vendor/adapter-sdk is up to date.");
}

main();
