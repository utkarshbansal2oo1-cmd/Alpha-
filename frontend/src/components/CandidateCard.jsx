import { memo, useMemo } from "react";
import { motion } from "framer-motion";
import { MapPin, Building2, CheckCircle2, Activity } from "lucide-react";
import { getSourceBadge } from "../lib/sourceGroups";

// Sprint 22: evidence is the hierarchy, not the score. The overall match
// score still exists (recruiters do want a sortable number) but it's a
// small, secondary label -- not a giant ring dominating the card. What
// dominates is a short, real evidence list built from whatever the
// backend actually reported for this candidate: match.reasons (the
// Matching Engine's own explanation), plus, for GitHub-sourced
// candidates, github_quality_score/github_repositories_analyzed/
// github_last_activity -- every line here traces to a real response
// field, nothing is invented copy.
function buildEvidenceLines(candidate, match) {
  const lines = [];
  for (const reason of match?.reasons || []) {
    lines.push(reason);
  }
  if (candidate.github_repositories_analyzed != null) {
    lines.push(`${candidate.github_repositories_analyzed} repositories analyzed`);
  }
  if (candidate.github_last_activity) {
    const days = Math.round((Date.now() - new Date(candidate.github_last_activity).getTime()) / 86400000);
    if (days <= 14) lines.push(days <= 1 ? "Active in the last day" : `Active ${days} days ago`);
  }
  return lines.slice(0, 4);
}

function relativeActivity(dateStr) {
  if (!dateStr) return null;
  const days = Math.round((Date.now() - new Date(dateStr).getTime()) / 86400000);
  if (days <= 1) return "Active today";
  if (days <= 7) return `Active ${days}d ago`;
  if (days <= 30) return `Active ${Math.round(days / 7)}w ago`;
  return null;
}

function CandidateCard({ candidate, match, rank, onOpen, index }) {
  const evidence = useMemo(() => buildEvidenceLines(candidate, match), [candidate, match]);
  const isGithub = candidate.source === "github";
  const activity = isGithub ? relativeActivity(candidate.github_last_activity) : null;
  const score = Math.round(match?.overall_score ?? 0);
  // Sprint 36: every candidate card exposes its provenance, uniformly --
  // not just GitHub-sourced ones. Same lookup the Source Group section
  // headers use, so a card's badge always agrees with whichever section
  // it's rendered in (and still renders correctly for the flat-grid
  // fallback, where there's no section header at all).
  const sourceBadge = useMemo(() => getSourceBadge(candidate.source), [candidate.source]);

  return (
    <motion.button
      type="button"
      onClick={() => onOpen(candidate)}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: Math.min(index, 8) * 0.05, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ y: -3 }}
      className="glass-panel group flex flex-col gap-4 rounded-2xl p-5 text-left transition-shadow duration-200 hover:shadow-glow focus-visible:shadow-glow"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs text-ink-500">
            <span>#{rank}</span>
            {sourceBadge.label && (
              <span className="flex items-center gap-1">
                {sourceBadge.Icon && <sourceBadge.Icon className="h-3 w-3" strokeWidth={1.75} />}
                {sourceBadge.label}
              </span>
            )}
          </div>
          <h3 className="mt-1 truncate text-base font-semibold text-ink-100">{candidate.name}</h3>
          <p className="truncate text-sm text-ink-500">
            {candidate.role !== "Unknown" ? candidate.role : candidate.headline || "Role not specified"}
          </p>
        </div>
        {/* De-emphasized score: small label, not a dominant ring/percentage */}
        <div className="shrink-0 text-right">
          <span className="text-[10px] uppercase tracking-wide text-ink-500">Match</span>
          <p className="text-sm font-semibold tabular-nums text-ink-300">{score}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-500">
        {candidate.current_company && (
          <span className="flex items-center gap-1">
            <Building2 className="h-3 w-3" strokeWidth={1.75} />
            {candidate.current_company}
          </span>
        )}
        {candidate.location && (
          <span className="flex items-center gap-1">
            <MapPin className="h-3 w-3" strokeWidth={1.75} />
            {candidate.location}
          </span>
        )}
        {activity && (
          <span className="flex items-center gap-1 text-signal-green/80">
            <Activity className="h-3 w-3" strokeWidth={1.75} />
            {activity}
          </span>
        )}
        {isGithub && candidate.github_quality_score != null && (
          <span>Quality {Math.round(candidate.github_quality_score)}</span>
        )}
      </div>

      {/* Evidence: the card's primary visual weight */}
      {evidence.length > 0 && (
        <div className="space-y-1.5 border-t border-white/[0.06] pt-3">
          <p className="text-[10px] font-medium uppercase tracking-wide text-ink-500">Why this candidate</p>
          {evidence.map((line, i) => (
            <p key={i} className="flex items-start gap-1.5 text-xs text-ink-300">
              <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-signal-green" strokeWidth={2} />
              <span className="line-clamp-1">{line}</span>
            </p>
          ))}
        </div>
      )}

      {candidate.skills?.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {candidate.skills.slice(0, 5).map((skill) => (
            <span key={skill} className="rounded-full bg-white/[0.06] px-2.5 py-1 text-[11px] text-ink-300">
              {skill}
            </span>
          ))}
          {candidate.skills.length > 5 && (
            <span className="rounded-full bg-white/[0.03] px-2.5 py-1 text-[11px] text-ink-500">
              +{candidate.skills.length - 5}
            </span>
          )}
        </div>
      )}
    </motion.button>
  );
}

export default memo(CandidateCard);
