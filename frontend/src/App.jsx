import { Suspense, lazy, useCallback, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { smartSearch, SearchError } from "./api";
import SearchBar from "./components/SearchBar";
import DiscoveryTimeline from "./components/DiscoveryTimeline";
import CandidateGrid from "./components/CandidateGrid";
import EmptyState from "./components/EmptyState";
import CommandPalette from "./components/CommandPalette";

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
  const searchInputRef = useRef(null);

  const runSearch = useCallback(async (submittedQuery) => {
    setQuery(submittedQuery);
    setError(null);
    setResponse(null);
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

  const reset = useCallback(() => {
    setPhase("idle");
    setQuery("");
    setResponse(null);
    setError(null);
  }, []);

  const activeConnectorNames = useMemo(
    () => (response?.discovery?.connector_results || []).filter((c) => c.attempted).map((c) => c.source_name),
    [response]
  );

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
        {phase !== "idle" && (
          <button
            onClick={reset}
            className="flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.04] px-3.5 py-1.5 text-xs font-medium text-ink-300 transition-colors hover:bg-white/[0.08] hover:text-ink-100"
          >
            <RotateCcw className="h-3.5 w-3.5" strokeWidth={1.75} />
            New search
          </button>
        )}
      </header>

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
                  {response.count > 0 && (
                    <div className="mb-8 text-center">
                      <p className="text-sm text-ink-500">
                        {response.count} candidate{response.count === 1 ? "" : "s"} found for "{query}"
                      </p>
                    </div>
                  )}

                  {response.count > 0 ? (
                    <CandidateGrid candidates={response.candidates} rankings={response.rankings} />
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
