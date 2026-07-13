/**
 * Popup controller. Every state transition here is caused by either the
 * popup opening (triggers one extraction pass on the active tab) or the
 * recruiter clicking a button (capture / retry / debug) -- there is no
 * polling, no auto-refresh, and no background activity once the popup
 * closes.
 *
 * Sprint 13 changes:
 *  - Extraction results can now be a single candidate OR an array of
 *    candidates (e.g. from the career-page-listing adapter, which reads a
 *    whole company team page at once). The detected-state card shows a
 *    count and preview names when it's a list; "Add to AlphaSource" then
 *    captures every one of them.
 *  - A "Debug this page" footer link runs the visual debug overlay
 *    (adapter-sdk/debug/inspector.js) directly on the current tab, showing
 *    every adapter's detect() attempt and confidence, not just the winner.
 */

const states = ["loading", "no-candidate", "detected", "uploading", "success", "error"];

function showState(name) {
  for (const s of states) {
    document.getElementById(`state-${s}`).classList.toggle("hidden", s !== name);
  }
}

function setBadge(text) {
  document.getElementById("status-badge").textContent = text;
}

let currentTab = null;
let extractedFields = null;
let isMulti = false;

async function init() {
  showState("loading");
  setBadge("Scanning…");

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  currentTab = tab;
  document.getElementById("page-url").textContent = tab?.url || "";

  chrome.runtime.sendMessage({ type: "extract", tabId: tab.id }, (response) => {
    if (!response?.ok) {
      setBadge("Error");
      showState("error");
      document.getElementById("error-message").textContent =
        response?.error || "Could not scan this page.";
      return;
    }

    const { detected, fields, multi, adapterUsed } = response.result;
    if (!detected) {
      setBadge("No candidate found");
      showState("no-candidate");
      return;
    }

    extractedFields = fields;
    isMulti = Boolean(multi);
    setBadge(isMulti ? `${fields.length} candidates detected` : "Candidate detected");

    if (isMulti) {
      document.getElementById("candidate-name").textContent = `${fields.length} candidates found`;
      document.getElementById("candidate-headline").textContent = fields
        .slice(0, 3)
        .map((f) => f.name)
        .join(", ") + (fields.length > 3 ? ", …" : "");
      document.getElementById("candidate-meta").textContent = `Detected via ${adapterUsed}`;
    } else {
      document.getElementById("candidate-name").textContent = fields.name;
      document.getElementById("candidate-headline").textContent = fields.headline || fields.role || "";
      const metaParts = [fields.current_company, fields.location].filter(Boolean);
      document.getElementById("candidate-meta").textContent = metaParts.join(" · ");
    }

    document.getElementById("capture-button").textContent = isMulti
      ? `Add all ${fields.length} to AlphaSource`
      : "Add to AlphaSource";

    showState("detected");
  });
}

document.getElementById("capture-button").addEventListener("click", () => {
  if (!extractedFields) return;
  showState("uploading");

  chrome.runtime.sendMessage(
    { type: "capture", fields: extractedFields, pageUrl: currentTab?.url },
    (response) => {
      if (!response?.ok) {
        showState("error");
        document.getElementById("error-message").textContent =
          response?.error || "The upload failed.";
        return;
      }

      if (response.result.multi) {
        const count = response.result.results.length;
        document.getElementById("success-sub").textContent = `${count} candidates added to AlphaSource`;
      } else {
        const { created, candidate_id: candidateId } = response.result.result;
        document.getElementById("success-sub").textContent = created
          ? `New candidate created (ID: ${candidateId})`
          : `Merged into existing candidate (ID: ${candidateId})`;
      }
      showState("success");
    }
  );
});

document.getElementById("retry-button").addEventListener("click", init);

document.getElementById("options-link").addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

document.getElementById("debug-link").addEventListener("click", (e) => {
  e.preventDefault();
  if (!currentTab) return;
  setBadge("Opening debug overlay…");
  chrome.runtime.sendMessage({ type: "debug", tabId: currentTab.id }, (response) => {
    if (!response?.ok) {
      setBadge("Debug failed");
      return;
    }
    setBadge("Debug overlay shown on page");
    window.close(); // let the recruiter see the overlay on the actual page
  });
});

init();
