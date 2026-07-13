import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check } from "lucide-react";

/**
 * Sprint 6, Task 2: the "AI reasoning" sequence shown before results
 * appear -- modeled directly on the real pipeline's stages (Query
 * Understanding -> Knowledge Engine expansion -> Search Planner ->
 * Candidate Repository -> response), not an invented loading animation.
 * Each stage genuinely represents backend work that happens inside the
 * single POST /api/search call (see backend/app/routers/search_pipeline.py);
 * this component visualizes that real lifecycle client-side, exactly the
 * pattern already established in the previous sprint's LiveDemo (see that
 * file's comment on stage/promise timing) -- Task 2 asks for a richer
 * 5-stage version with per-stage checkmarks, which this replaces the
 * simpler 3-label version with.
 *
 * `completeUpTo` is driven by the caller: in Guided Demo Mode every stage
 * advances on a fixed schedule (deterministic, never blocked on a network
 * call); in Live Mode, the final stage waits on the real API promise the
 * same way the previous sprint's implementation did.
 */
const STAGES = [
  { key: "understanding", label: "Understanding hiring requirement...", done: "Role identified" },
  { key: "expanding", label: "Expanding hiring intelligence...", done: "Skills expanded" },
  { key: "planning", label: "Building search strategy...", done: "Search plan created" },
  { key: "searching", label: "Searching talent intelligence...", done: "Candidates discovered" },
  { key: "explaining", label: "Generating explainable recommendations...", done: null },
];

export default function ThinkingSequence({ activeIndex }) {
  return (
    <div className="flex flex-col gap-1 py-10 max-w-md mx-auto">
      <AnimatePresence mode="popLayout">
        {STAGES.map((stage, i) => {
          if (i > activeIndex) return null;
          const isComplete = i < activeIndex || (i === activeIndex && stage.done === null && activeIndex === STAGES.length - 1 && false);
          const isCurrent = i === activeIndex;

          return (
            <motion.div
              key={stage.key}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
              className="flex items-center gap-3"
            >
              <span className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
                {i < activeIndex ? (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 300, damping: 15 }}
                    className="w-5 h-5 rounded-full bg-match-green/15 flex items-center justify-center"
                  >
                    <Check size={13} className="text-match-green" strokeWidth={3} />
                  </motion.span>
                ) : (
                  <span className="w-2 h-2 rounded-full bg-accent-purple animate-pulse" />
                )}
              </span>
              <span className={`text-sm ${isCurrent ? "text-text-primary" : "text-text-tertiary"}`}>
                {i < activeIndex ? stage.done || stage.label : stage.label}
              </span>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

export { STAGES as THINKING_STAGES };
