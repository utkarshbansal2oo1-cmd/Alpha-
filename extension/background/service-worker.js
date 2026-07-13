/**
 * Background service worker -- the only place that talks to the AlphaSource
 * backend. Three responsibilities, all strictly reactive to an explicit
 * message from popup.js (never triggered on a timer, a page load, or any
 * event the recruiter didn't directly cause):
 *
 * 1. "extract" -- inject the Adapter SDK's core + adapter files (per
 *    vendor/adapter-sdk/manifest.json) plus content-scripts/extractor.js
 *    into the active tab and return whatever they find. This only runs
 *    while the popup is open (i.e. the recruiter just clicked the
 *    extension icon).
 * 2. "capture" -- POST the (optionally recruiter-edited) extracted fields
 *    to POST /candidate/import on the configured backend, and return the
 *    result. This only runs when the recruiter clicks "Add to AlphaSource"
 *    in the popup. Supports both a single candidate and an array of
 *    candidates (e.g. from the career-page-listing adapter) -- each is
 *    POSTed individually so the existing, unmodified /candidate/import
 *    contract (one candidate per request) never needed to change.
 * 3. "debug" -- inject the same adapter files plus
 *    vendor/adapter-sdk/debug/inspector.css + inspector.js, then run the
 *    on-page visual debug overlay (see docs/ADAPTER_SDK.md's debug-mode
 *    section). Only runs when the recruiter clicks "Debug this page" in
 *    the popup -- same one-click, no-background-activity contract as
 *    extract/capture.
 *
 * Sprint 13 change: the adapter file list is no longer hardcoded here.
 * It's read from vendor/adapter-sdk/manifest.json, which
 * scripts/sync-adapter-sdk-to-extension.js regenerates from whatever
 * adapters currently exist in adapter-sdk/adapters/. Adding a new adapter
 * therefore never requires touching this file.
 */

async function loadAdapterFileList() {
  const manifestUrl = chrome.runtime.getURL("vendor/adapter-sdk/manifest.json");
  const response = await fetch(manifestUrl);
  const manifest = await response.json();
  return manifest.files.map((f) => `vendor/adapter-sdk/${f}`);
}

async function extractFromActiveTab(tabId) {
  const adapterFiles = await loadAdapterFileList();

  await chrome.scripting.executeScript({
    target: { tabId },
    files: [...adapterFiles, "content-scripts/extractor.js"],
  });

  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => window.__alphaSourceExtractCandidate(),
  });

  return result;
}

async function debugActiveTab(tabId) {
  const adapterFiles = await loadAdapterFileList();

  await chrome.scripting.insertCSS({
    target: { tabId },
    files: ["vendor/adapter-sdk/debug/inspector.css"],
  });

  await chrome.scripting.executeScript({
    target: { tabId },
    files: [...adapterFiles, "vendor/adapter-sdk/debug/inspector.js"],
  });

  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => window.__AlphaSourceDebugInspector.run(),
  });

  return result;
}

async function getSettings() {
  const stored = await chrome.storage.sync.get(["backendUrl", "capturedBy"]);
  return {
    backendUrl: stored.backendUrl || "http://localhost:8000",
    capturedBy: stored.capturedBy || null,
  };
}

function toImportPayload(fields, pageUrl, capturedBy) {
  return {
    name: fields.name,
    role: fields.role || undefined,
    headline: fields.headline || undefined,
    current_company: fields.current_company || undefined,
    experience_years: fields.experience_years || undefined,
    skills: fields.skills || [],
    location: fields.location || undefined,
    summary: fields.summary || undefined,
    education: fields.education || [],
    public_profile_url: fields.public_profile_url || pageUrl,
    resume_link: fields.resume_link || undefined,
    source_type: "browser_extension",
    source_url: pageUrl,
    captured_by: capturedBy || undefined,
  };
}

async function postOneCandidate(fields, pageUrl, backendUrl, capturedBy) {
  const payload = toImportPayload(fields, pageUrl, capturedBy);

  const response = await fetch(`${backendUrl.replace(/\/$/, "")}/candidate/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(body.detail || `Import failed with status ${response.status}`);
  }

  return body;
}

async function captureCandidate(fields, pageUrl) {
  const { backendUrl, capturedBy } = await getSettings();

  if (Array.isArray(fields)) {
    const results = [];
    for (const entry of fields) {
      results.push(await postOneCandidate(entry, pageUrl, backendUrl, capturedBy));
    }
    return { multi: true, results };
  }

  const result = await postOneCandidate(fields, pageUrl, backendUrl, capturedBy);
  return { multi: false, result };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "extract") {
    extractFromActiveTab(message.tabId)
      .then((result) => sendResponse({ ok: true, result }))
      .catch((err) => sendResponse({ ok: false, error: String(err?.message || err) }));
    return true; // keep the message channel open for the async response
  }

  if (message?.type === "capture") {
    captureCandidate(message.fields, message.pageUrl)
      .then((result) => sendResponse({ ok: true, result }))
      .catch((err) => sendResponse({ ok: false, error: String(err?.message || err) }));
    return true;
  }

  if (message?.type === "debug") {
    debugActiveTab(message.tabId)
      .then((result) => sendResponse({ ok: true, result }))
      .catch((err) => sendResponse({ ok: false, error: String(err?.message || err) }));
    return true;
  }

  return false;
});
