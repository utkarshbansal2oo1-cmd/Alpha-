import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Sparkles, Radio } from "lucide-react";
import SectionHeading from "../ui/SectionHeading";
import AiUnderstoodPanel from "../demo/AiUnderstoodPanel";
import CandidateCard from "../demo/CandidateCard";
import SummaryBar from "../demo/SummaryBar";
import CandidateDrawer from "../demo/CandidateDrawer";
import ThinkingSequence, { THINKING_STAGES } from "../demo/ThinkingSequence";
import DiscoveryStages from "../demo/DiscoveryStages";
import { searchCandidates, searchCandidatesSmart } from "../demo/api";
import { DEMO_SCENARIOS, getScenarioForQuery } from "../../data/demoScenarios";

const EXAMPLE_PLACEHOLDER = "Find Product Engineers with AWS and Kubernetes in Bangalore";

// Per-stage dwell time for Guided Demo Mode: fixed, deterministic, always
// inside the 300-500ms window requested for Task 2 -- never a random
// delay, so the sequence's total runtime is identical on every run, which
// matters for a live presentation with a rehearsed pace.
const DEMO_STAGE_DELAYS = [400, 450, 400, 450, 350];
const LIVE_STAGE_DELAY = 450;
// Sprint 18: dwell time per Discovery Orchestrator stage when it actually
// ran -- the stage list itself is dynamic (comes from the backend), only
// the reveal pacing is fixed here, same reasoning as LIVE_STAGE_DELAY.
const DISCOVERY_STAGE_DELAY = 500;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Sprint 6: LiveDemo now offers two modes.
 *
 * - "Guided Demo" (default): deterministic, offline, pre-loaded example
 *   queries resolved entirely against src/data/demoScenarios.js. Zero
 *   network calls -- cannot fail, cannot be slow, cannot return an
 *   unexpected empty result live in front of executives (Task 8).
 * - "Live Pipeline": the real POST /api/search call against the actual
 *   backend, exactly as built in the previous sprint -- kept for technical
 *   audiences who want to see the real system, not just a rehearsed demo.
 *
 * Both modes share the same ThinkingSequence, AiUnderstoodPanel,
 * SummaryBar, CandidateCard, and CandidateDrawer components -- the
 * difference is only where the requirement/search_plan/candidates data
 * comes from.
 */
export default function LiveDemo() {
  const [mode, setMode] = useState("guided"); // "guided" | "live"
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("idle"); // idle | thinking | success | error
  const [stageIndex, setStageIndex] = useState(0);
  const [candidates, setCandidates] = useState([]);
  const [requirement, setRequirement] = useState(null);
  const [searchPlan, setSearchPlan] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  // Sprint 19: per-candidate Matching Engine scores, keyed by candidate id
  // -- only populated in Live Pipeline mode (POST /api/search/smart
  // returns `rankings`; Guided Demo mode has no backend call and no
  // scores, so CandidateCard falls back to its original WhyMatchedTag
  // presentation when this is empty).
  const [matchByCandidateId, setMatchByCandidateId] = useState({});
  // Sprint 18: Discovery Orchestrator progress, only populated (and only
  // rendered) when a live search actually triggers discovery.
  const [discovery, setDiscovery] = useState(null);
  const [discoveryStageIndex, setDiscoveryStageIndex] = useState(0);

  async function runGuidedDemo(exampleQuery) {
    const scenario = getScenarioForQuery(exampleQuery);
    if (!scenario) return;

    setQuery(exampleQuery);
    setStatus("thinking");
    setErrorMessage("");

    for (let i = 0; i < THINKING_STAGES.length; i++) {
      setStageIndex(i);
      await sleep(DEMO_STAGE_DELAYS[i]);
    }

    setCandidates(scenario.candidates);
    setRequirement(scenario.requirement);
    setSearchPlan(scenario.search_plan);
    setStatus("success");
  }

  async function runLiveSearch(e) {
    e.preventDefault();
    if (!query.trim()) return;

    setStatus("thinking");
    setErrorMessage("");
    setDiscovery(null);
    setDiscoveryStageIndex(0);

    // Sprint 18: calls the Autonomous Discovery Engine's endpoint instead
    // of the plain pipeline -- same requirement/search_plan/candidates
    // shape, plus `discovery`, describing whether the Discovery
    // Orchestrator needed to search connected sources for more
    // candidates. POST /api/search (searchCandidates) is untouched and
    // still available; this is the new, additive path.
    const resultPromise = searchCandidatesSmart(query.trim());

    try {
      for (let i = 0; i < THINKING_STAGES.length - 1; i++) {
        setStageIndex(i);
        await sleep(LIVE_STAGE_DELAY);
      }
      setStageIndex(THINKING_STAGES.length - 1);

      // Final stage stays on screen until the real response resolves,
      // however long that takes -- reveal is gated on the actual API,
      // never a timer, so a slow backend is reflected honestly.
      const data = await resultPromise;

      if (data.discovery?.triggered && data.discovery.stages?.length) {
        // Discovery actually ran (existing repository results weren't
        // sufficient) -- reveal its stage list before showing the
        // refreshed shortlist, exactly like the sprint brief's example
        // progress sequence.
        setDiscovery(data.discovery);
        setStatus("discovering");
        for (let i = 0; i < data.discovery.stages.length; i++) {
          setDiscoveryStageIndex(i);
          await sleep(DISCOVERY_STAGE_DELAY);
        }
      }

      setCandidates(data.candidates || []);
      setRequirement(data.requirement || null);
      setSearchPlan(data.search_plan || null);
      // Sprint 19: `rankings` -- each candidate's MatchResult + rank, in
      // the same order as `candidates` -- keyed here by candidate id so
      // CandidateCard can look its own score up in O(1).
      const byId = {};
      for (const ranked of data.rankings || []) {
        byId[ranked.candidate_id] = ranked;
      }
      setMatchByCandidateId(byId);
      setStatus("success");
    } catch (err) {
      setErrorMessage(err.message || "Something went wrong while searching.");
      setStatus("error");
    }
  }

  function switchMode(nextMode) {
    setMode(nextMode);
    setStatus("idle");
    setQuery("");
    setCandidates([]);
    setRequirement(null);
    setSearchPlan(null);
    setErrorMessage("");
    setDiscovery(null);
    setDiscoveryStageIndex(0);
    setMatchByCandidateId({});
  }

  const isThinking = status === "thinking";
  const isDiscovering = status === "discovering";

  return (
    <section id="demo" className="relative py-40 px-5">
      <div className="max-w-[1000px] mx-auto">
        <SectionHeading
          eyebrow="Live Product Demo"
          title="Try it. Right now."
          subtitle="The real AlphaSource pipeline -- Query Understanding, Knowledge Engine, and Candidate Repository -- not a mockup."
        />

        <div className="flex justify-center mb-8">
          <div className="glass-plane-2 rounded-full p-1 flex gap-1" role="tablist" aria-label="Demo mode">
            <ModeTab
              active={mode === "guided"}
              onClick={() => switchMode("guided")}
              icon={Sparkles}
              label="Guided Demo"
            />
            <ModeTab
              active={mode === "live"}
              onClick={() => switchMode("live")}
              icon={Radio}
              label="Live Pipeline"
            />
          </div>
        </div>

        <div className="glass-plane-3 rounded-3xl p-6 md:p-10">
          {mode === "guided" ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-text-tertiary text-center mb-1">
                Choose a pre-loaded scenario -- deterministic, offline, presentation-safe.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {DEMO_SCENARIOS.map((scenario) => (
                  <button
                    key={scenario.query}
                    onClick={() => runGuidedDemo(scenario.query)}
                    disabled={isThinking || isDiscovering}
                    className="text-left px-5 py-4 rounded-xl bg-white/[0.03] border border-white/10 hover:border-accent-blue/40 hover:bg-white/[0.05] transition-all text-sm text-text-secondary hover:text-text-primary disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-cyan"
                  >
                    {scenario.query}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <form onSubmit={runLiveSearch} className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-text-tertiary" size={18} />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={EXAMPLE_PLACEHOLDER}
                  aria-label="Describe the candidate you need"
                  className="w-full pl-11 pr-4 py-4 rounded-xl bg-white/[0.03] border border-white/10 text-text-primary placeholder:text-text-tertiary outline-none focus:border-accent-blue/50 focus:ring-2 focus:ring-accent-blue/20 transition-all"
                />
              </div>
              <button
                type="submit"
                disabled={isThinking || isDiscovering}
                className="px-8 py-4 rounded-xl bg-accent-gradient text-white font-semibold disabled:opacity-60 disabled:cursor-not-allowed transition-opacity focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-cyan"
              >
                {isThinking ? "Searching…" : isDiscovering ? "Discovering…" : "Search"}
              </button>
            </form>
          )}

          <div className="mt-2 min-h-[120px]">
            <AnimatePresence mode="wait">
              {isThinking && (
                <motion.div key="thinking" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <ThinkingSequence activeIndex={stageIndex} />
                </motion.div>
              )}

              {isDiscovering && discovery && (
                <motion.div
                  key="discovering"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="rounded-xl border border-accent-purple/20 bg-accent-purple/[0.04] p-6"
                >
                  <p className="text-xs uppercase tracking-wide text-accent-purple font-semibold mb-4">
                    Autonomous Discovery Engine
                  </p>
                  <DiscoveryStages stages={discovery.stages} activeIndex={discoveryStageIndex} />
                </motion.div>
              )}

              {status === "error" && (
                <motion.div
                  key="error"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="rounded-xl border border-red-500/20 bg-red-500/5 p-6 text-center mt-6"
                >
                  <p className="font-medium text-red-300">Search failed</p>
                  <p className="mt-1 text-sm text-red-300/70">{errorMessage}</p>
                </motion.div>
              )}

              {status === "success" && candidates.length === 0 && (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="rounded-xl border border-white/10 bg-white/[0.02] p-8 text-center mt-6"
                >
                  {discovery?.triggered ? (
                    <>
                      <p className="font-medium text-text-primary">
                        No suitable candidates were found across your connected talent sources.
                      </p>
                      <p className="mt-1 text-sm text-text-secondary">
                        AlphaSource searched your internal repository and every connected source
                        before giving up -- try broadening the requirement, or connect an
                        additional source (Greenhouse, resume uploads, CSV import).
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="font-medium text-text-primary">No candidates found</p>
                      <p className="mt-1 text-sm text-text-secondary">
                        Try a broader search -- dropping a location or skill constraint.
                      </p>
                    </>
                  )}
                </motion.div>
              )}

              {status === "success" && candidates.length > 0 && (
                <motion.div key="results" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-6">
                  <AiUnderstoodPanel requirement={requirement} />
                  <SummaryBar candidates={candidates} />
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {candidates.map((candidate, i) => (
                      <CandidateCard
                        key={candidate.id}
                        candidate={candidate}
                        searchPlan={searchPlan}
                        index={i}
                        onSelect={setSelectedCandidate}
                        match={matchByCandidateId[candidate.id]}
                      />
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      <CandidateDrawer
        candidate={selectedCandidate}
        searchPlan={searchPlan}
        onClose={() => setSelectedCandidate(null)}
      />
    </section>
  );
}

function ModeTab({ active, onClick, icon: Icon, label }) {
  return (
    <button
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-cyan ${
        active ? "bg-accent-gradient text-white" : "text-text-tertiary hover:text-text-primary"
      }`}
    >
      <Icon size={14} />
      {label}
    </button>
  );
}
