/**
 * Options page: stores only two values via chrome.storage.sync -- the
 * backend URL and a self-reported recruiter identity string. Never stores
 * a password, session cookie, or any authentication token for any site the
 * recruiter might capture candidates from -- there is nothing here to
 * bypass any site's login.
 */
async function load() {
  const stored = await chrome.storage.sync.get(["backendUrl", "capturedBy"]);
  document.getElementById("backend-url").value = stored.backendUrl || "";
  document.getElementById("captured-by").value = stored.capturedBy || "";
}

document.getElementById("save").addEventListener("click", async () => {
  const backendUrl = document.getElementById("backend-url").value.trim();
  const capturedBy = document.getElementById("captured-by").value.trim();

  await chrome.storage.sync.set({ backendUrl, capturedBy });

  const status = document.getElementById("status");
  status.textContent = "Saved.";
  setTimeout(() => (status.textContent = ""), 2000);
});

load();
