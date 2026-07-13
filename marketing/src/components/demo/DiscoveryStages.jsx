import { motion, AnimatePresence } from "framer-motion";
import { Check } from "lucide-react";

/**
 * Sprint 18: renders the Discovery Orchestrator's stage list (returned as
 * `discovery.stages` from POST /api/search/smart) the same way
 * ThinkingSequence renders its own fixed 5-stage list -- one row per
 * stage, revealed up to `activeIndex`, with a checkmark for completed
 * stages and a pulsing dot for the current one. Unlike ThinkingSequence,
 * the stage list itself comes from the backend (it depends on which
 * connectors actually ran), not a hardcoded constant, since the whole
 * point of this sprint is that discovery is dynamic -- it may run zero,
 * one, or several connectors depending on what the recruiter searched
 * for and what's connected.
 */
export default function DiscoveryStages({ stages, activeIndex }) {
  if (!stages || stages.length === 0) return null;

  return (
    <div className="flex flex-col gap-2" aria-live="polite">
      <AnimatePresence mode="popLayout">
        {stages.map((stage, i) => {
          if (i > activeIndex) return null;
          const isDone = i < activeIndex;
          const isCurrent = i === activeIndex;

          return (
            <motion.div
              key={`${stage.label}-${i}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
              className="flex items-start gap-3 text-sm"
            >
              {isDone ? (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 300, damping: 15 }}
                  className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-match-green/20 text-match-green"
                >
                  <Check size={11} strokeWidth={3} />
                </motion.div>
              ) : (
                <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-accent-purple animate-pulse" />
              )}
              <div>
                <p className={isDone ? "text-text-secondary" : "text-text-primary font-medium"}>
                  {stage.label}
                  {typeof stage.count === "number" ? ` (${stage.count})` : ""}
                </p>
                {stage.detail && isDone && (
                  <p className="text-xs text-text-tertiary mt-0.5">{stage.detail}</p>
                )}
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
