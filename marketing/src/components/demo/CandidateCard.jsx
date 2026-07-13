import { motion } from "framer-motion";
import WhyMatchedTag from "./WhyMatchedTag";
import { useCursorGlow } from "../../hooks/useCursorGlow";

/** Dark-glass port of frontend/src/App.jsx's CandidateCard. Same fields,
 * same layout logic -- only the visual chrome changes to match the
 * marketing site's plane-2 glass surface instead of the product's light
 * theme card.
 *
 * Sprint 6, Task 4/5: cards are now clickable (mouse and keyboard) to open
 * the CandidateDrawer, with a cursor-tracked glow and hover-lift matching
 * the feature cards elsewhere on the site, so this interaction feels
 * consistent with the rest of the product rather than a one-off.
 *
 * Sprint 19: an optional `match` prop -- one entry from POST
 * /api/search/smart's `rankings` (a RankedCandidate: { rank, match:
 * MatchResult } ) -- adds an Overall Match Score badge plus Health/
 * Confidence chips and the Matching Engine's own `reasons` list. Only
 * Live Pipeline mode supplies this (Guided Demo mode has no backend call
 * and no scores); when absent the card renders exactly as before,
 * falling back to WhyMatchedTag's client-side-computed reasoning. */
export default function CandidateCard({ candidate, searchPlan, index, onSelect, match }) {
  const { onMouseMove } = useCursorGlow();
  const overallScore = match?.match?.overall_score;
  const healthScore = match?.match?.component_scores?.health;
  const confidenceScore = match?.match?.component_scores?.confidence;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -3 }}
      transition={{ duration: 0.4, delay: index * 0.08, ease: [0.16, 1, 0.3, 1] }}
      onMouseMove={onMouseMove}
      onClick={() => onSelect?.(candidate)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect?.(candidate);
        }
      }}
      aria-label={`View full profile for ${candidate.name}`}
      className="group cursor-glow glass-plane-2 rounded-xl p-5 hover:border-white/20 hover:shadow-glow-card transition-all duration-200 cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-cyan"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-text-primary">{candidate.name}</h3>
          <p className="text-sm text-text-secondary">{candidate.role}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          {typeof overallScore === "number" && (
            <span className="whitespace-nowrap rounded-full bg-match-green/15 border border-match-green/25 px-3 py-1 text-xs font-semibold text-match-green">
              {Math.round(overallScore)}% match
            </span>
          )}
          <span className="whitespace-nowrap rounded-full bg-white/5 px-3 py-1 text-xs font-medium text-text-tertiary">
            {candidate.source}
          </span>
        </div>
      </div>

      {(typeof healthScore === "number" || typeof confidenceScore === "number") && (
        <div className="mt-3 flex gap-2 text-[11px] text-text-tertiary">
          {typeof healthScore === "number" && <span>Health {Math.round(healthScore)}%</span>}
          {typeof healthScore === "number" && typeof confidenceScore === "number" && <span>&middot;</span>}
          {typeof confidenceScore === "number" && <span>Confidence {Math.round(confidenceScore)}%</span>}
        </div>
      )}

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm text-text-secondary">
        <div>
          <dt className="text-text-tertiary">Experience</dt>
          <dd>{candidate.experience} yrs</dd>
        </div>
        <div>
          <dt className="text-text-tertiary">Location</dt>
          <dd>{candidate.location}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-text-tertiary">Current company</dt>
          <dd>{candidate.current_company}</dd>
        </div>
      </dl>

      {candidate.skills?.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {candidate.skills.map((skill) => (
            <span
              key={skill}
              className="rounded-full bg-accent-blue/10 border border-accent-blue/20 px-2.5 py-1 text-xs font-medium text-accent-cyan"
            >
              {skill}
            </span>
          ))}
        </div>
      )}

      {match?.match?.reasons?.length > 0 ? (
        <div className="mt-4 rounded-lg bg-match-green/10 border border-match-green/20 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-match-green">
            Why matched
          </p>
          <ul className="mt-1 space-y-0.5 text-sm text-match-green/90">
            {match.match.reasons.map((reason) => (
              <li key={reason}>&bull; {reason}</li>
            ))}
          </ul>
        </div>
      ) : (
        <WhyMatchedTag candidate={candidate} searchPlan={searchPlan} />
      )}

      <span className="mt-4 inline-block text-xs font-medium text-accent-cyan opacity-0 group-hover:opacity-100 transition-opacity">
        View full profile &rarr;
      </span>
    </motion.div>
  );
}
