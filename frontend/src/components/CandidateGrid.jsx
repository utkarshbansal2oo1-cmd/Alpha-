import { useMemo, useState } from "react";
import CandidateCard from "./CandidateCard";
import CandidateDrawer from "./CandidateDrawer";

// Joins the flat `candidates` list against `rankings` (candidate_id ->
// match + rank) exactly as the backend returns them -- both come back
// from the same /api/search/smart response, already in final ranked
// order. No client-side re-sorting, re-filtering, or score fabrication.
export default function CandidateGrid({ candidates, rankings }) {
  const [selected, setSelected] = useState(null);

  const matchById = useMemo(() => {
    const map = new Map();
    for (const r of rankings || []) map.set(r.candidate_id, r);
    return map;
  }, [rankings]);

  if (!candidates?.length) return null;

  return (
    <div className="mx-auto w-full max-w-6xl">
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
              onOpen={setSelected}
            />
          );
        })}
      </div>

      <CandidateDrawer
        candidate={selected}
        match={selected ? matchById.get(selected.id)?.match : null}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
