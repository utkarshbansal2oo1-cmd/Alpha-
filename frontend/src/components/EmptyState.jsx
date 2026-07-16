import { motion } from "framer-motion";
import { Search, ShieldCheck, SlidersHorizontal, Radio } from "lucide-react";

// Sprint 22: never render a bare "No candidates found." A recruiter
// needs to know the system actually searched -- what it searched, how
// many candidates it evaluated, and why none qualified -- before they
// can trust a zero result. Every number/label here comes straight from
// the real DiscoveryRun (discovery.connector_results, discovery.decision)
// already in the /api/search/smart response; the only invented text is
// the generic, always-applicable suggestion copy at the bottom.
//
// Sprint 38 fix: `discovery.decision.reason` is the Discovery Decision
// Engine's reasoning for *triggering* discovery in the first place --
// computed BEFORE any connector ran, against whatever the internal
// candidate pool looked like at that moment. This component used to show
// that reason as if it explained the empty page the recruiter is looking
// at -- misleading whenever discovery actually ran, found real
// candidates (visible right above in "per-connector results" as N found/
// qualified), and THIS page is still empty for a completely different,
// LATER reason: none of those candidates cleared the adaptive
// relevance_threshold applied to page 1 (see discovery_search.py's
// smart_search()). Real-world example that surfaced this: a GitHub
// search returned 114 enriched profiles, but the query asked for
// "10 years experience in Delhi" -- signals GitHub's API cannot verify
// for any candidate -- so every one of them scored low on those specific
// dimensions and none reached the bar, even though their skills matched
// fine. The two reasons are now shown as what they are: the discovery
// engine's own decision log (secondary), and, when candidates truly were
// found but held back by the score threshold, a primary explanation of
// exactly that, plus a direct action to see them anyway.
export default function EmptyState({
  discovery,
  query,
  relevanceThreshold,
  weakMatchCount,
  totalAllCandidates,
  onShowWeakMatches,
  showingWeakMatches,
}) {
  const connectorResults = discovery?.connector_results || [];
  const attempted = connectorResults.filter((c) => c.attempted);
  const evaluated = connectorResults.reduce((sum, c) => sum + (c.candidates_found || 0), 0);
  const decisionReason = discovery?.decision?.reason;

  // True whenever candidates were genuinely found/scored (post-discovery)
  // but every one of them fell below relevance_threshold for this page --
  // the real, current-state explanation, distinct from the pre-discovery
  // decision log above.
  const heldBackByThreshold = (totalAllCandidates || 0) > 0 && (weakMatchCount || 0) > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel mx-auto max-w-2xl rounded-2xl p-8"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/[0.06]">
          <Search className="h-5 w-5 text-ink-300" strokeWidth={1.75} />
        </div>
        <div>
          <p className="font-medium text-ink-100">No candidates matched "{query}"</p>
          <p className="mt-1 text-sm text-ink-500">
            AlphaSource searched live -- here's exactly what it did.
          </p>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="rounded-xl bg-white/[0.03] p-4">
          <p className="flex items-center gap-1.5 text-xs text-ink-500">
            <Radio className="h-3.5 w-3.5" strokeWidth={1.75} />
            Connectors searched
          </p>
          <p className="mt-1 text-xl font-semibold text-ink-100">{attempted.length}</p>
        </div>
        <div className="rounded-xl bg-white/[0.03] p-4">
          <p className="flex items-center gap-1.5 text-xs text-ink-500">
            <ShieldCheck className="h-3.5 w-3.5" strokeWidth={1.75} />
            Candidates evaluated
          </p>
          <p className="mt-1 text-xl font-semibold text-ink-100">{evaluated}</p>
        </div>
        <div className="rounded-xl bg-white/[0.03] p-4">
          <p className="flex items-center gap-1.5 text-xs text-ink-500">
            <SlidersHorizontal className="h-3.5 w-3.5" strokeWidth={1.75} />
            Confidence threshold
          </p>
          <p className="mt-1 text-xl font-semibold text-ink-100">
            {relevanceThreshold != null
              ? Math.round(relevanceThreshold)
              : discovery?.decision?.min_confidence_threshold != null
              ? Math.round(discovery.decision.min_confidence_threshold)
              : "—"}
          </p>
        </div>
      </div>

      {connectorResults.length > 0 && (
        <div className="mt-6">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-500">Per-connector results</p>
          <ul className="space-y-1.5">
            {connectorResults.map((c) => (
              <li key={c.source_name} className="flex items-center justify-between text-sm">
                <span className="capitalize text-ink-300">{c.source_name.replace(/_/g, " ")}</span>
                <span className="text-ink-500">
                  {!c.configured
                    ? "not connected"
                    : !c.attempted
                    ? "skipped"
                    : c.error
                    ? `error: ${c.error}`
                    : `${c.candidates_found} found, ${c.candidates_imported} qualified`}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {heldBackByThreshold ? (
        <div className="mt-6 rounded-lg bg-white/[0.03] px-4 py-3">
          <p className="text-sm text-ink-300">
            {totalAllCandidates} candidate{totalAllCandidates === 1 ? "" : "s"} were found and scored, but{" "}
            {weakMatchCount} of them scored below the {relevanceThreshold != null ? Math.round(relevanceThreshold) : ""}%
            confidence bar for this search -- often because the query asks for something a data source can't verify
            (e.g. exact years of experience or a specific city), not because the skills don't match.
          </p>
          {onShowWeakMatches && (
            <button
              onClick={onShowWeakMatches}
              disabled={showingWeakMatches}
              className="mt-3 rounded-full border border-white/[0.08] bg-white/[0.04] px-4 py-1.5 text-xs font-medium text-ink-100 transition-colors hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {showingWeakMatches ? "Loading…" : `Show ${weakMatchCount} weaker match${weakMatchCount === 1 ? "" : "es"} anyway`}
            </button>
          )}
        </div>
      ) : (
        decisionReason && (
          <p className="mt-6 rounded-lg bg-white/[0.03] px-4 py-3 text-sm text-ink-500">
            <span className="mr-1 text-xs uppercase tracking-wide text-ink-500/80">Why this search ran:</span>
            {decisionReason}
          </p>
        )
      )}

      <div className="mt-6 border-t border-white/[0.06] pt-5">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-500">Try next</p>
        <ul className="space-y-1.5 text-sm text-ink-300">
          <li>• Broaden the requirement -- drop a location or a specific technology constraint</li>
          <li>• Confirm a relevant connector is configured for this kind of role</li>
          <li>• Reduce the confidence threshold if this role is niche or emerging</li>
        </ul>
      </div>
    </motion.div>
  );
}
