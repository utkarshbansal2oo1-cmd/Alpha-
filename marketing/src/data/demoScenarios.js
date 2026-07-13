import { DEMO_CANDIDATES } from "./candidates";

/**
 * Guided Demo Mode (Sprint 6, Task 8): pre-loaded, deterministic scenarios
 * for executive presentations. Each scenario pre-computes its own
 * requirement/search_plan/candidates shape -- identical in structure to
 * the real backend's SearchQueryResponse (see
 * backend/app/routers/search_pipeline.py) -- but resolved entirely
 * client-side against DEMO_CANDIDATES, with zero network calls. This is
 * what makes "the demo must never fail during a presentation" true: there
 * is nothing to fail. The real Live Demo mode (calling the actual backend)
 * remains available separately for technical audiences who want to see
 * the live pipeline.
 *
 * The matching logic below (role/skill intersection, lightweight
 * "expansion" for the AI Understood panel) mirrors -- but does not
 * replace or modify -- the real Search Planner's strict/expanded model.
 * It exists only so Guided Demo Mode's UI can render the same shapes the
 * real pipeline produces; it is not a new backend module and never talks
 * to the real Search Planner or Knowledge Engine.
 */

const KNOWLEDGE_EXPANSIONS = {
  AWS: [
    { value: "EC2", weight: 0.9 },
    { value: "Lambda", weight: 0.85 },
    { value: "S3", weight: 0.8 },
  ],
  Kubernetes: [
    { value: "EKS", weight: 0.88 },
    { value: "Docker", weight: 0.82 },
  ],
  "Machine Learning": [
    { value: "TensorFlow", weight: 0.85 },
    { value: "PyTorch", weight: 0.8 },
  ],
  "Backend Engineer": [
    { value: "Platform Engineer", weight: 0.75 },
    { value: "API Engineer", weight: 0.7 },
  ],
  "Product Engineer": [
    { value: "Backend Engineer", weight: 0.72 },
    { value: "Frontend Engineer", weight: 0.68 },
  ],
};

function buildPlan(role, skills) {
  const strict = [
    { field_type: "role", canonical_id: role, canonical_value: role },
    ...skills.map((s) => ({ field_type: "skill", canonical_id: s, canonical_value: s })),
  ];

  const expanded = [];
  const weights = {};
  for (const term of [role, ...skills]) {
    const expansions = KNOWLEDGE_EXPANSIONS[term] || [];
    for (const exp of expansions) {
      expanded.push({
        field_type: skills.includes(term) ? "skill" : "role",
        source_canonical_id: term,
        expanded_id: exp.value,
        expanded_value: exp.value,
        weight: exp.weight,
        notes: "",
      });
      weights[exp.value] = exp.weight;
    }
  }

  const search_terms = [
    ...new Set([role, ...skills, ...expanded.map((e) => e.expanded_value)]),
  ];

  return {
    strict,
    expanded,
    search_terms,
    weights,
    unresolved: [],
    knowledge_versions: { roles: "demo-1.0.0", skills: "demo-1.0.0" },
  };
}

function matchCandidates(plan) {
  const normalized = new Set(plan.search_terms.map((t) => t.toLowerCase()));
  return DEMO_CANDIDATES.filter((c) => {
    const roleMatch = normalized.has(c.role.toLowerCase());
    const skillMatch = c.skills.some((s) => normalized.has(s.toLowerCase()));
    return roleMatch || skillMatch;
  });
}

function scenario(query, role, skills) {
  const requirement = { role, skills };
  const search_plan = buildPlan(role, skills);
  const candidates = matchCandidates(search_plan);
  return {
    query,
    requirement,
    search_plan,
    candidates,
    count: candidates.length,
  };
}

export const DEMO_SCENARIOS = [
  scenario(
    "Find Backend Engineers with 5+ years, skilled in AWS and Kubernetes",
    "Backend Engineer",
    ["AWS", "Kubernetes"]
  ),
  scenario(
    "Product Engineers in Bangalore with strong system design experience",
    "Product Engineer",
    ["System Design", "React"]
  ),
  scenario(
    "Machine Learning engineers with production ML experience",
    "Machine Learning Engineer",
    ["Machine Learning", "PyTorch"]
  ),
  scenario(
    "Platform engineers who have run Kubernetes at scale",
    "Platform Engineer",
    ["Kubernetes", "AWS"]
  ),
];

export function getScenarioForQuery(query) {
  return DEMO_SCENARIOS.find((s) => s.query === query) || null;
}
