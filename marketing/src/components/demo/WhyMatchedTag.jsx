/**
 * Direct port of frontend/src/App.jsx's computeWhyMatched -- purely
 * presentational, explains which of the SearchPlan's strict terms this
 * candidate's role/skills intersect with. No new scoring logic; identical
 * to the real product's behavior.
 */
export function computeWhyMatched(candidate, searchPlan) {
  if (!searchPlan?.strict) return [];

  const candidateSkillsLower = new Set(
    (candidate.skills || []).map((s) => s.trim().toLowerCase())
  );
  const candidateRoleLower = (candidate.role || "").trim().toLowerCase();

  const reasons = [];
  for (const filter of searchPlan.strict) {
    const value = filter.canonical_value;
    const valueLower = value.trim().toLowerCase();

    if (filter.field_type === "role" && valueLower === candidateRoleLower) {
      reasons.push(`Role matches "${value}"`);
    } else if (filter.field_type === "skill" && candidateSkillsLower.has(valueLower)) {
      reasons.push(`Has required skill "${value}"`);
    }
  }
  return reasons;
}

export default function WhyMatchedTag({ candidate, searchPlan }) {
  const reasons = computeWhyMatched(candidate, searchPlan);
  if (reasons.length === 0) return null;

  return (
    <div className="mt-4 rounded-lg bg-match-green/10 border border-match-green/20 p-3">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-match-green">
        Why matched
      </p>
      <ul className="mt-1 space-y-0.5 text-sm text-match-green/90">
        {reasons.map((reason) => (
          <li key={reason}>&bull; {reason}</li>
        ))}
      </ul>
    </div>
  );
}
