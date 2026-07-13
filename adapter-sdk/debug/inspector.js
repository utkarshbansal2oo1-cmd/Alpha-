/**
 * Visual debug mode -- an on-page overlay for developing/verifying a new
 * adapter without needing devtools or console.log. Injects a floating
 * panel (bottom-right) listing every registered adapter's detect()
 * attempt (matched/confidence/timing/error), highlights the winning
 * adapter's row, shows the extracted+normalized fields, and outlines the
 * actual DOM elements the winning adapter's locateElements() reports
 * using (if it implements that optional hook -- see core/base-adapter.js).
 *
 * Not part of the extraction pipeline itself -- purely observational. Run
 * it by injecting inspector.css + inspector.js (after the usual
 * core/adapter files) and calling window.__AlphaSourceDebugInspector.run().
 * In the extension, this is wired to a "Debug this page" link in the
 * popup (see extension/popup/popup.js) that opens the current tab's page
 * with the overlay active instead of relying only on the popup's own,
 * smaller preview.
 */
(function () {
  function highlightElements(elements) {
    (elements || []).forEach((el) => {
      if (el && el.classList) el.classList.add("alphasource-debug-highlight");
    });
  }

  function clearHighlights() {
    document
      .querySelectorAll(".alphasource-debug-highlight")
      .forEach((el) => el.classList.remove("alphasource-debug-highlight"));
  }

  function renderPanel(traceResult) {
    const existing = document.getElementById("alphasource-debug-panel");
    if (existing) existing.remove();

    const panel = document.createElement("div");
    panel.id = "alphasource-debug-panel";

    const rows = traceResult.trace
      .slice()
      .sort((a, b) => b.confidence - a.confidence)
      .map((t) => {
        const isWinner = t.adapter === traceResult.adapterUsed;
        const cls = t.error ? "asdbg-error" : isWinner ? "asdbg-winner" : "";
        return `<tr class="${cls}">
          <td>${t.adapter}</td>
          <td>${t.matched ? "yes" : "no"}</td>
          <td>${t.confidence.toFixed(2)}</td>
          <td>${t.detectMs.toFixed(2)}ms</td>
          <td>${t.error ? "error" : ""}</td>
        </tr>`;
      })
      .join("");

    const fieldsJson = traceResult.matched
      ? JSON.stringify(traceResult.fields, null, 2)
      : "(no adapter matched)";

    panel.innerHTML = `
      <div class="asdbg-header">
        AlphaSource Adapter Debug
        <span class="asdbg-close" id="asdbg-close">✕</span>
      </div>
      <div class="asdbg-body">
        <table>
          <thead><tr><th>Adapter</th><th>Matched</th><th>Conf.</th><th>Time</th><th></th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
        <div><strong>Winner:</strong> ${traceResult.adapterUsed || "none"}</div>
        <div><strong>Valid:</strong> ${traceResult.valid}</div>
        <div class="asdbg-fields">${fieldsJson}</div>
      </div>
    `;

    document.body.appendChild(panel);
    document.getElementById("asdbg-close").addEventListener("click", () => {
      panel.remove();
      clearHighlights();
    });
  }

  function run() {
    const sdk = window.__AlphaSourceSDK || {};
    const registry = new sdk.AdapterRegistry();
    Object.values(sdk.adapters || {}).forEach((adapter) => registry.register(adapter));

    const input = sdk.SourceInput.fromDocument(document, { url: document.location.href });
    const result = registry.runPipeline(input);

    clearHighlights();
    renderPanel(result);

    if (result.matched) {
      const winningAdapter = Object.values(sdk.adapters || {}).find((a) => a.name === result.adapterUsed);
      if (winningAdapter && typeof winningAdapter.locateElements === "function") {
        try {
          highlightElements(winningAdapter.locateElements(input));
        } catch (e) {
          // Highlighting is best-effort only -- never let it break the panel.
        }
      }
    }

    return result;
  }

  window.__AlphaSourceDebugInspector = { run, clearHighlights };
})();
