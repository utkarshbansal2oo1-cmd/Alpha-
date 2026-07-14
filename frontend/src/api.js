// Sprint 21 rewrite: the recruiter product now calls the REAL Discovery
// Engine entry point (POST /api/search/smart), not the older POST
// /api/search pipeline this file used to call. /api/search/smart is
// strictly additive on top of that older endpoint (see
// backend/app/routers/discovery_search.py's own docstring) -- it runs
// Query Understanding -> Search Planner -> Candidate Repository, then,
// if the Discovery Decision Engine decides the existing pool isn't
// enough, invokes every connected connector (GitHub, Greenhouse, etc.)
// live, imports what they find, and re-scores/re-ranks everything with
// the Matching + Ranking Engines -- all in one HTTP round trip.
//
// There is no server-sent/streamed version of this endpoint today: it
// returns one JSON response containing the full `discovery.stages`
// list describing what already happened. The UI (see
// DiscoveryTimeline.jsx) animates a staged reveal of those real stages
// after the response lands, rather than fabricating a fake progress bar
// disconnected from the actual pipeline -- every stage label, detail,
// and count rendered is exactly what the backend reports happened.
const API_ROOT = import.meta.env.VITE_API_ROOT_URL || "https://alpha-production-426e.up.railway.app";

export class SearchError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "SearchError";
    this.status = status;
  }
}

/**
 * Calls POST /api/search/smart with the recruiter's raw free-text
 * requirement. Returns the full SmartSearchResponse: session_id,
 * requirement, search_plan, candidates, count, discovery (the
 * DiscoveryRun -- stages, connector_results, whether discovery actually
 * triggered), and rankings (each candidate's real match score + reasons,
 * in final ranked order).
 *
 * Sprint 33: this runs the ENTIRE pipeline (Query Understanding ->
 * Search Planner -> Discovery -> Matching -> Ranking) exactly once and
 * persists the ranked output server-side as a search session --
 * `session_id` in the response identifies it. Getting page 2+ of THIS
 * SAME search must go through `getSearchSessionPage` below, not another
 * call to this function -- calling smartSearch() again always starts a
 * brand-new search (new Query Understanding call, new session), per the
 * backend's explicit contract (see discovery_search.py's docstring).
 *
 * Throws SearchError with a message suitable for direct display on
 * validation (422) or upstream failures (502 -- e.g. Query Understanding's
 * LLM call failed), and on network failure.
 */
export async function smartSearch(query, page = 1, pageSize = 20) {
  let res;
  try {
    res = await fetch(`${API_ROOT}/api/search/smart`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, page, page_size: pageSize }),
    });
  } catch {
    throw new SearchError(
      "Could not reach the Discovery Engine. The backend may be offline.",
      0
    );
  }

  if (!res.ok) {
    let detail = `Search failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // Response body wasn't JSON -- keep the generic message above.
    }
    throw new SearchError(detail, res.status);
  }

  return res.json();
}

/**
 * Calls GET /api/search/session/{sessionId} -- pages through a search
 * that already ran, WITHOUT repeating Query Understanding, Search
 * Planner, Discovery, Matching, or Ranking (see discovery_search.py's
 * get_search_session_page()). Returns the exact same SmartSearchResponse
 * shape smartSearch() does, so the UI renders a page identically
 * regardless of which function produced it.
 *
 * Sprint 33: this is what "Next page" / "Load More" should call once a
 * session_id exists -- never smartSearch() again for the same search.
 */
export async function getSearchSessionPage(sessionId, page, pageSize = 20) {
  let res;
  try {
    res = await fetch(
      `${API_ROOT}/api/search/session/${encodeURIComponent(sessionId)}?page=${page}&page_size=${pageSize}`
    );
  } catch {
    throw new SearchError(
      "Could not reach the Discovery Engine. The backend may be offline.",
      0
    );
  }

  if (!res.ok) {
    let detail = `Could not load page ${page} (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // Response body wasn't JSON -- keep the generic message above.
    }
    throw new SearchError(detail, res.status);
  }

  return res.json();
}

/**
 * GET /connectors -- which real data sources are actually wired up and
 * authorized right now (GitHub, Greenhouse, etc.), each with a live
 * health flag. Used to render an honest "connected sources" indicator
 * rather than a static list of logos that may not reflect reality.
 */
export async function getConnectors() {
  try {
    const res = await fetch(`${API_ROOT}/connectors`);
    if (!res.ok) return [];
    const body = await res.json();
    return Array.isArray(body) ? body : body.connectors || [];
  } catch {
    return [];
  }
}
