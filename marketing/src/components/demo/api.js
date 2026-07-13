// Identical contract to frontend/src/api.js (the recruiter product) --
// intentionally not reinvented, since the Live Demo section's entire
// purpose is to call the real, already-tested backend pipeline, not a
// marketing-site mock. Same env var name so both apps can point at the
// same backend via .env without translation.
const API_ROOT = import.meta.env.VITE_API_ROOT_URL || "http://localhost:8000";

export async function searchCandidates(query) {
  let res;
  try {
    res = await fetch(`${API_ROOT}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
  } catch (networkErr) {
    throw new Error("Could not reach the search service. Is the backend running?");
  }

  if (!res.ok) {
    let detail = `Search failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response body wasn't JSON -- fall back to the generic message above
    }
    throw new Error(detail);
  }

  return res.json();
}

// Sprint 18: calls the new POST /api/search/smart endpoint (the
// Autonomous Talent Discovery Engine) instead of the plain /api/search
// pipeline. Same request/response contract, plus a `discovery` field
// describing whether the Discovery Orchestrator ran and what it found --
// see app/routers/discovery_search.py. POST /api/search itself is
// untouched and searchCandidates() above still works exactly as before.
export async function searchCandidatesSmart(query) {
  let res;
  try {
    res = await fetch(`${API_ROOT}/api/search/smart`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
  } catch (networkErr) {
    throw new Error("Could not reach the search service. Is the backend running?");
  }

  if (!res.ok) {
    let detail = `Search failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response body wasn't JSON -- fall back to the generic message above
    }
    throw new Error(detail);
  }

  return res.json();
}
