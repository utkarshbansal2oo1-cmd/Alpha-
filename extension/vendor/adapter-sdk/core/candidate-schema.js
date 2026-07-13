/**
 * The one shared output shape every adapter's normalize() must produce,
 * and the shape validate() checks against by default. Intentionally the
 * same field set as the backend's CandidateImportRequest
 * (backend/app/candidate_repository/import_schemas.py) -- the SDK's output
 * is designed to be POSTed to /candidate/import unchanged. Keeping one
 * canonical field list here (instead of duplicating it in every adapter)
 * is what makes adapters "small": an adapter only needs to map its source
 * format onto these names.
 */
const CANDIDATE_FIELDS = {
  name: { required: true, type: "string" },
  role: { required: false, type: "string" },
  headline: { required: false, type: "string" },
  current_company: { required: false, type: "string" },
  experience_years: { required: false, type: "number" },
  skills: { required: false, type: "array" },
  location: { required: false, type: "string" },
  summary: { required: false, type: "string" },
  education: { required: false, type: "array" },
  public_profile_url: { required: false, type: "string" },
  resume_link: { required: false, type: "string" },
};

function typeOf(value) {
  if (Array.isArray(value)) return "array";
  if (value === null || value === undefined) return "undefined";
  return typeof value;
}

function validateOne(fields) {
  const errors = [];

  for (const [key, spec] of Object.entries(CANDIDATE_FIELDS)) {
    const value = fields ? fields[key] : undefined;
    const present = value !== undefined && value !== null && value !== "";

    if (spec.required && !present) {
      errors.push(`Missing required field: ${key}`);
      continue;
    }
    if (present && typeOf(value) !== spec.type) {
      errors.push(`Field "${key}" expected type ${spec.type}, got ${typeOf(value)}`);
    }
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Validates either a single candidate-fields object, or an array of them
 * (for "multi" adapters like a company career/team page that extract many
 * candidates from one page -- see adapters/career-page-listing.js). An
 * array is valid only if every entry is valid; errors are prefixed with
 * the entry's index so a caller can tell which record failed.
 */
function validateCandidateFields(fields) {
  if (Array.isArray(fields)) {
    const errors = [];
    for (let i = 0; i < fields.length; i++) {
      const result = validateOne(fields[i]);
      for (const e of result.errors) errors.push(`[${i}] ${e}`);
    }
    return { valid: errors.length === 0 && fields.length > 0, errors };
  }
  return validateOne(fields);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { CANDIDATE_FIELDS, validateCandidateFields };
}
if (typeof window !== "undefined") {
  window.__AlphaSourceSDK = Object.assign(window.__AlphaSourceSDK || {}, {
    candidateSchema: { CANDIDATE_FIELDS, validateCandidateFields },
  });
}
