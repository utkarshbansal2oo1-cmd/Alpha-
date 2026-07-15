import { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Github, RotateCcw } from "lucide-react";
import { getIntegrationsStatus, getSearchSessionPage, smartSearch, SearchError } from "./api";
import SearchBar from "./components/SearchBar";
import DiscoveryTimeline from "./components/DiscoveryTimeline";
import CandidateGrid from "./components/CandidateGrid";
import EmptyState from "./components/EmptyState";
import CommandPalette from "./components/CommandPalette";
import GithubConnectModal from "./components/GithubConnectModal";

// Performance: the R3F scene (three.js + fiber) is one of the heaviest
// dependencies in this bundle -- lazy-loaded so it's not on the
// critical path for first paint, and Suspense-gated with a null
// fallback (blank space, not a spinner) while it loads.
const DiscoveryCore = lazy(() => import("./components/DiscoveryCore"));

// Sprint 22: full visual redesign. This IS the app -- there is no
// separate marketing page above it, no demo mode, no sample searches,
// no predefined role list. A recruiter's first interaction is a real
// search box wired directly to POST /api/search/smart -- the live
// Discovery Engine -- and every state below reflects exactly what that
// one endpoint call actually did.
//
// Phases:
//   idle       -- the search box, nothing else.
//   requesting -- the request is in flight; the Discovery Core pulses
//                 to communicate "working" -- no spinner anywhere.
//   discovering-- the response has landed; DiscoveryTimeline replays the
//                 REAL discovery.stages the backend reports, and the
//                 Discovery Core's orbit nodes light up for whichever
//                 connectors discovery.connector_results says were
//                 actually attempted.
//   results    -- ranked candidates, each with real evidence, or a rich
//                 empty state explaining exactly what was searched.
//   error      -- the request failed; the real error detail is shown.

export default function App() {
  const [phase, setPhase] = useState("idle");
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  // Sprint 31: which page of the already-ranked pool is on screen, and
  // whether a page turn is in flight. Deliberately a *separate* flag from
  // `phase` -- turning the page must not replay the "requesting" ->
  // "discovering" pipeline animation (DiscoveryTimeline), since no new
  // discovery is happening, just a slice of the same ranked results the
  // recruiter already saw discovered once.
  const [pageLoading, setPageLoading] = useState(false);
  const [pageError, setPageError] = useState(null);
  const searchInputRef = useRef(null);

  // Sprint 37: GitHub connector onboarding. `githubStatus` mirrors the
  // `github` key from GET /integrations/status -- fetched once on mount
  // so the header icon and the "not connected" banner both reflect real
  // backend state from the first render, not an assumed default.
  const [githubStatus, setGithubStatus] = useState(null);
  const [githubModalOpen, setGithubModalOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getIntegrationsStatus().then((data) => {
      if (!cancelled) setGithubStatus(data.github);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const runSearch = useCallback(async (submittedQuery) => {
    setQuery(submittedQuery);
    setError(null);
    setResponse(null);
    setPageError(null);
    setPhase("requesting");
    try {
      const data = await smartSearch(submittedQuery);
      setResponse(data);
      setPhase("discovering");
    } catch (err) {
      setError(err instanceof SearchError ? err : new SearchError(String(err?.message || err)));
      setPhase("error");
    }
  }, []);

  const goToPage = useCallback(
    async (targetPage) => {
      if (!response || pageLoading) return;
      if (targetPage < 1 || targetPage > response.total_pages) return;
      setPageLoading(true);
      setPageError(null);
      try {
        // Sprint 33: pages through the SAME search session the first
        // response created (response.session_id) -- deliberately NOT
        // another smartSearch() call, which would re-run Query
        // Understanding/Search Planner/Discovery/Matching/Ranking and
        // could even start a brand-new, unrelated session.
        const data = await getSearchSessionPage(response.session_id, targetPage, response.page_size);
        setResponse(data);
      } catch (err) {
        setPageError(err instanceof SearchError ? err : new SearchError(String(err?.message || err)));
      } finally {
        setPageLoading(false);
      }
    },
    [response, pageLoading]
  );

  const reset = useCallback(() => {
    setPhase("idle");
    setQuery("");
    setResponse(null);
    setError(null);
    setPageError(null);
    setPageLoading(false);
  }, []);

  const activeConnectorNames = useMemo(
    () => (response?.discovery?.connector_results || []).filter((c) => c.attempted).map((c) => c.source_name),
    [response]
  );

  // Sprint 37 objective 4: never let seed fallback pass silently -- if
  // this search's own discovery run shows GitHub was never configured
  // AND seed fallback is why the recruiter is seeing suggested profiles,
  // say so explicitly with a way to fix it right there.
  const githubNotConnectedInThisRun = useMemo(() => {
    if (!response?.seed_fallback_used) return false;
    const githubResult = (response?.discovery?.connector_results || []).find(
      (c) => c.source_name?.toLowerCase() === "github"
    );
    return githubResult ? githubResult.configured === false : !githubStatus?.configured;
  }, [response, githubStatus]);

  const scenePhase = phase === "requesting" || phase === "discovering" ? "searching" : phase === "results" ? "results" : "idle";
  const isHome = phase === "idle";

  return (
    <div className="relative min-h-screen overflow-hidden bg-void-950">
      <CommandPalette onFocusSearch={() => searchInputRef.current?.focus()} onNewSearch={reset} />

      {/* Ambient background -- gradient wash + noise, no imagery */}
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-10%,rgba(110,92,240,0.18),transparent)]" />
      <div className="noise-overlay pointer-events-none fixed inset-0 opacity-[0.03]" />

      <header className="relative z-20 flex items-center justify-between px-6 py-6 sm:px-10">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-accent-500 text-sm font-bold text-white">
            A
          </div>
          <span className="text-sm font-semibold tracking-tight text-ink-100">AlphaSource</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setGithubModalOpen(true)}
            className={`flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors ${
              githubStatus?.configured
                ? "border-signal-green/30 bg-signal-green/10 text-signal-green hover:bg-signal-green/20"
                : "border-white/[0.08] bg-white/[0.04] text-ink-300 hover:bg-white/[0.08] hover:text-ink-100"
            }`}
          >
            <Github className="h-3.5 w-3.5" strokeWidth={1.75} />
            {githubStatus?.configured ? "GitHub connected" : "Connect GitHub"}
          </button>
          {phase !== "idle" && (
            <button
              onClick={reset}
              className="flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.04] px-3.5 py-1.5 text-xs font-medium text-ink-300 transition-colors hover:bg-white/[0.08] hover:text-ink-100"
            >
              <RotateCcw className="h-3.5 w-3.5" strokeWidth={1.75} />
              New search
            </button>
          )}
        </div>
      </header>

      <GithubConnectModal
        open={githubModalOpen}
        onClose={() => setGithubModalOpen(false)}
        status={githubStatus}
        onStatusChange={setGithubStatus}
      />

      <main className="relative z-10 mx-auto flex min-h-[calc(100vh-88px)] max-w-6xl flex-col items-center px-6 pb-24">
        <div
          className={`relative w-full transition-all duration-700 ease-out ${
            isHome ? "flex flex-1 flex-col items-center justify-center" : "pt-10"
          }`}
        >
          <Suspense fallback={null}>
            <DiscoveryCore
              phase={scenePhase}
              activeConnectorNames={activeConnectorNames}
              className={`pointer-events-none absolute left-1/2 -translate-x-1/2 transition-all duration-700 ease-out ${
                isHome ? "top-1/2 h-[460px] w-[460px] -translate-y-[58%]" : "top-0 h-[240px] w-[240px] -translate-y-1/4 opacity-70"
              }`}
            />
          </Suspense>

          <div className="relative z-10 flex flex-col items-center">
            {isHome && (
              <motion.h1
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                className="mb-10 max-w-2xl text-center text-hero font-semibold text-ink-100"
              >
                Describe who you need.
                <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent-400 to-accent-600">
                  AlphaSource finds them.
                </span>
              </motion.h1>
            )}

            <SearchBar
              ref={searchInputRef}
              onSearch={runSearch}
              disabled={phase === "requesting"}
              initialValue={query}
            />
          </div>
        </div>

        <AnimatePresence mode="wait">
          {phase === "requesting" && (
            <motion.div
              key="requesting"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="mt-16 text-center"
            >
              <p className="text-sm text-ink-500">Connecting to the Discovery Engine…</p>
            </motion.div>
          )}

          {(phase === "discovering" || phase === "results") && response && (
            <motion.div key="pipeline" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-16 w-full">
              {phase === "discovering" && (
                <DiscoveryTimeline
                  discovery={response.discovery}
                  requirement={response.requirement}
                  onComplete={() => setPhase("results")}
                />
              )}

              {phase === "results" && (
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
                  {response.total_count > 0 && (
                    <div className="mb-8 text-center">
                      <p className="text-sm text-ink-500">
                        {response.total_count} candidate{response.total_count === 1 ? "" : "s"} found for "{query}"
                        {response.total_pages > 1 && (
                          <span className="text-ink-600"> · page {response.page} of {response.total_pages}</span>
                        )}
                      </p>
                    </div>
                  )}

                  {githubNotConnectedInThisRun && (
                    <div className="mb-6 flex items-center gap-3 rounded-xl border border-accent-500/25 bg-accent-500/[0.06] px-4 py-3">
                      <Github className="h-4 w-4 shrink-0 text-accent-400" strokeWidth={1.75} />
                      <p className="flex-1 text-xs text-ink-300">
                        GitHub is not connected. Showing suggested profiles until a live talent source is connected.
                      </p>
                      <button
                        onClick={() => setGithubModalOpen(true)}
                        className="shrink-0 rounded-full bg-accent-500 px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-accent-600"
                      >
                        Connect
                      </button>
                    </div>
                  )}

                  {response.total_count > 0 ? (
                    <>
                      <CandidateGrid
                        candidates={response.candidates}
                        rankings={response.rankings}
                        sourceGroups={response.source_groups}
                      />

                      {response.total_pages > 1 && (
                        <div className="mt-10 flex flex-col items-center gap-3">
                          {pageError && (
                            <p className="text-xs text-signal-red">{pageError.message}</p>
                          )}
                          <div className="flex items-center gap-3">
                            <button
                              onClick={() => goToPage(response.page - 1)}
                              disabled={response.page <= 1 || pageLoading}
                              className="rounded-full border border-white/[0.08] bg-white/[0.04] px-4 py-1.5 text-xs font-medium text-ink-300 transition-colors hover:bg-white/[0.08] hover:text-ink-100 disabled:cursor-not-allowed disabled:opacity-40"
                            >
                              Previous
                            </button>
                            <span className="text-xs text-ink-500">
                              {pageLoading ? "Loading…" : `Page ${response.page} of ${response.total_pages}`}
                            </span>
                            <button
                              onClick={() => goToPage(response.page + 1)}
                              disabled={response.page >= response.total_pages || pageLoading}
                              className="rounded-full border border-white/[0.08] bg-white/[0.04] px-4 py-1.5 text-xs font-medium text-ink-300 transition-colors hover:bg-white/[0.08] hover:text-ink-100 disabled:cursor-not-allowed disabled:opacity-40"
                            >
                              Next
                            </button>
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <EmptyState discovery={response.discovery} query={query} />
                  )}
                </motion.div>
              )}
            </motion.div>
          )}

          {phase === "error" && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-panel mt-16 flex max-w-lg items-start gap-3 rounded-2xl p-6"
            >
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-signal-red" strokeWidth={1.75} />
              <div>
                <p className="font-medium text-ink-100">The search couldn't complete</p>
                <p className="mt-1 text-sm text-ink-500">{error?.message}</p>
                <button
                  onClick={() => runSearch(query)}
                  className="mt-4 rounded-full bg-white/[0.06] px-4 py-1.5 text-xs font-medium text-ink-300 transition-colors hover:bg-white/[0.1] hover:text-ink-100"
                >
                  Try again
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
