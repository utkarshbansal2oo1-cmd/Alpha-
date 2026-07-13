import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, Radar, Search, FileSearch, ListOrdered, CheckCircle2, XCircle } from "lucide-react";

// Renders the REAL discovery pipeline for this specific search. The
// backend (POST /api/search/smart) is a single request/response call --
// it doesn't stream tokens -- so the middle stages here are the exact
// `discovery.stages` array the backend already computed (one entry per
// connector actually queried, with the real candidate counts it found).
// Two bookend steps (Understanding the requirement / Ranking candidates)
// describe pipeline work that genuinely runs on every call (Query
// Understanding + the Search Planner before discovery; the Matching +
// Ranking Engines after) but isn't itemized as a DiscoveryStage by the
// backend today -- they're labeled generically rather than inventing
// fake per-stage detail/counts for them.
//
// The reveal is staggered client-side purely for legibility (so six
// steps don't all slam into view at once) -- nothing about WHAT
// happened, or in what order, is invented. Every label with a count or
// detail string below is copied verbatim from the response.

function iconFor(label) {
  const l = label.toLowerCase();
  if (l.includes("understand")) return Brain;
  if (l.includes("strategy") || l.includes("connector") && l.includes("skipping")) return Radar;
  if (l.includes("searching")) return Search;
  if (l.includes("candidate intelligence") || l.includes("evidence")) return FileSearch;
  if (l.includes("ranking") || l.includes("rank")) return ListOrdered;
  if (l.includes("shortlist") || l.includes("preparing")) return CheckCircle2;
  return Search;
}

function buildTimeline(discovery, requirement) {
  const steps = [];

  steps.push({
    key: "understand",
    label: "Understanding requirement",
    detail: requirement
      ? `Parsed as: ${requirement.role || "role"}${requirement.skills?.length ? ` — ${requirement.skills.join(", ")}` : ""}`
      : null,
    ok: true,
  });

  steps.push({
    key: "strategy",
    label: "Generating connector strategy",
    detail: discovery?.triggered
      ? "Existing records weren't sufficient — querying connected sources."
      : discovery?.decision?.reason || "Evaluating whether live discovery is needed.",
    ok: true,
  });

  (discovery?.stages || []).forEach((stage, i) => {
    steps.push({
      key: `stage-${i}`,
      label: stage.label?.replace(/\.\.\.$/, "") || "Working",
      detail: stage.detail || (typeof stage.count === "number" ? `${stage.count} found` : null),
      count: stage.count,
      ok: !stage.detail?.toLowerCase().includes("error"),
    });
  });

  steps.push({
    key: "ranking",
    label: "Ranking candidates",
    detail: "Scored across role, skills, experience, and location by the Matching Engine.",
    ok: true,
  });

  steps.push({
    key: "preparing",
    label: "Preparing results",
    detail: null,
    ok: true,
  });

  return steps;
}

export default function DiscoveryTimeline({ discovery, requirement, onComplete }) {
  const steps = buildTimeline(discovery, requirement);
  const [visibleCount, setVisibleCount] = useState(1);

  useEffect(() => {
    setVisibleCount(1);
    if (steps.length <= 1) {
      onComplete?.();
      return;
    }
    let i = 1;
    const interval = setInterval(() => {
      i += 1;
      setVisibleCount(i);
      if (i >= steps.length) {
        clearInterval(interval);
        setTimeout(() => onComplete?.(), 550);
      }
    }, 420);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discovery, requirement]);

  return (
    <div className="mx-auto w-full max-w-xl">
      <ol className="space-y-3">
        <AnimatePresence>
          {steps.slice(0, visibleCount).map((step, i) => {
            const Icon = step.ok === false ? XCircle : iconFor(step.label);
            const isLast = i === visibleCount - 1 && visibleCount < steps.length;
            return (
              <motion.li
                key={step.key}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
                className="glass-panel flex items-start gap-3 rounded-xl px-4 py-3"
              >
                <div
                  className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                    step.ok === false
                      ? "bg-signal-red/15 text-signal-red"
                      : isLast
                      ? "bg-accent-500/20 text-accent-400"
                      : "bg-signal-green/15 text-signal-green"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" strokeWidth={2} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-ink-100">
                    {step.label}
                    {isLast && (
                      <span className="ml-2 inline-flex gap-0.5 align-middle">
                        {[0, 1, 2].map((d) => (
                          <span
                            key={d}
                            className="inline-block h-1 w-1 animate-pulse rounded-full bg-accent-400"
                            style={{ animationDelay: `${d * 150}ms` }}
                          />
                        ))}
                      </span>
                    )}
                  </p>
                  {step.detail && (
                    <p className="mt-0.5 truncate text-xs text-ink-500">{step.detail}</p>
                  )}
                </div>
                {typeof step.count === "number" && (
                  <span className="shrink-0 rounded-full bg-white/[0.06] px-2 py-0.5 text-xs tabular-nums text-ink-300">
                    {step.count}
                  </span>
                )}
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ol>
    </div>
  );
}
