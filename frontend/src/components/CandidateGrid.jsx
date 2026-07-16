import { useMemo, useState } from "react";
import CandidateCard from "./CandidateCard";
import CandidateDrawer from "./CandidateDrawer";
import { getIconForKey } from "../lib/sourceGroups";

// Sprint 36: when the backend response includes `sourceGroups` (a
// presentation-layer partition of the SAME globally-ranked
// candidates/rankings below -- see app/routers/discovery_search.py's
// _build_source_groups()), render one section per Source Group instead
// of a single flat grid. Falls back to the original flat grid whenever
// sourceGroups is empty or absent (e.g. an older cached response shape),
// so this is purely additive: candidates/rankings themselves, and the
// order candidates appear within a group, are completely unchanged --
// only how they're visually bucketed and labeled.
export default function CandidateGrid({ candidates, rankings, sourceGroups }) {
  const [selected, setSelected] = useState(null);

  // Built from the FLAT `rankings` list (the one globally-ranked pool),
  // not from any per-group slice -- so the drawer/lookup always reflects
  // each candidate's real global rank and match, no matter which section
  // it was opened from.
  const matchById = useMemo(() => {
    const map = new Map();
    for (const r of rankings || []) map.set(r.candidate_id, r);
    return map;
  }, [rankings]);

  if (!candidates?.length) return null;

  const hasGroups = Array.isArray(sourceGroups) && sourceGroups.length > 0;

  return (
    <div className="mx-auto w-full max-w-6xl space-y-10">
      {hasGroups ? (
        sourceGroups.map((group) => (
          <SourceGroupSection key={group.source} group={group} matchById={matchById} onOpen={setSelected} />
        ))
      ) : (
        <CandidateSectionGrid candidates={candidates} matchById={matchById} onOpen={setSelected} />
      )}

      <CandidateDrawer
        candidate={selected}
        match={selected ? matchById.get(selected.id)?.match : null}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}

// One Source Group's section: a header (icon, display_name -- never the
// word "seed" even for the fallback group, since the backend's
// display_name already reads "Suggested Profiles" -- plus the honest
// counts the backend actually computed) followed by that group's own
// candidate grid. `is_fallback` gets a subdued "Suggested" pill instead
// of hiding or de-emphasizing the whole section -- recruiters should
// still see and be able to open these candidates, just clearly labeled.
//
// Sprint 38 fix: `qualified_count` (from discovery_search.py) counts how
// many of this source's candidates made it into the full ranked SESSION
// pool -- NOT how many cleared the relevance_threshold for this page.
// A seed-fallback group can show "9 searched, 9 qualified" while only 1
// of those 9 actually scored high enough to appear below (candidate_count).
// The label now says "in pool" instead of "qualified" to avoid implying
// all of them passed the confidence bar, and calls out candidate_count
// explicitly whenever it's smaller.
function SourceGroupSection({ group, matchById, onOpen }) {
  const Icon = getIconForKey(group.icon);

  return (
    <section>
      <header className="mb-3 flex flex-wrap items-baseline justify-between gap-2 border-b border-white/[0.06] pb-2">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-ink-300" strokeWidth={1.75} />
          <h2 className="text-sm font-semibold text-ink-100">{group.display_name}</h2>
          <span className="text-xs text-ink-500">{group.candidate_count}</span>
          {group.is_fallback && (
            <span className="rounded-full bg-white/[0.06] px-2 py-0.5 text-[10px] uppercase tracking-wide text-ink-500">
              Suggested
            </span>
          )}
        </div>
        {(group.searched_count > 0 || group.qualified_count > 0) && (
          <p className="text-[11px] text-ink-500">
            {group.searched_count} searched &middot; {group.qualified_count} in pool
            {group.qualified_count > group.candidate_count && (
              <span> &middot; {group.candidate_count} shown here</span>
            )}
          </p>
        )}
      </header>
      <CandidateSectionGrid candidates={group.candidates} matchById={matchById} onOpen={onOpen} />
    </section>
  );
}

function CandidateSectionGrid({ candidates, matchById, onOpen }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {candidates.map((candidate, index) => {
        const ranking = matchById.get(candidate.id);
        return (
          <CandidateCard
            key={candidate.id}
            candidate={candidate}
            match={ranking?.match}
            rank={ranking?.rank ?? index + 1}
            index={index}
            onOpen={onOpen}
          />
        );
      })}
    </div>
  );
}
