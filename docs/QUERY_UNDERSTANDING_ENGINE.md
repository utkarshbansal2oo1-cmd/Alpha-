# Query Understanding Engine — Design Document

Status: **Proposal — not implemented.** This document defines a `JobRequirement`
schema that is significantly larger than the one currently in
`backend/app/schemas.py` (`role`, `min_experience_yrs`, `location`,
`must_have_skills`, `nice_to_have_skills`). Adopting it is a schema change
that will affect `services/matching_engine.py`, `services/query_parser.py`,
the API contract, and eventually the `searches` table. Per direction, no code
changes will be made until this is reviewed and approved.

---

## 1. Why this exists

Every downstream module — matching, ranking, connectors, search — needs one
stable contract to consume. If each module parsed recruiter text itself, five
modules would disagree about what "7+ years" or "FinTech" means. The Query
Understanding Engine's only job is to be the single place where messy
recruiter language becomes one structured object, so everything downstream
can be dumb and deterministic.

Recruiters write requirements the way they'd say them out loud, not the way
a form would ask for them. The schema below is reverse-engineered from what
recruiters actually say (see the seven examples in the brief) rather than
from what's convenient to parse.

## 2. Design principles

1. **Every field must be independently useful to at least one downstream
   consumer.** No field exists "because it might be nice."
2. **The AI should never be forced to guess.** Fields it can't confidently
   fill are `null`/empty, not hallucinated. Confidence and ambiguity are
   first-class, not swept under the rug.
3. **Provider-agnostic.** Nothing in the schema or the population rules
   references Gemini, OpenAI, or any vendor. The engine is "a function from
   text to JobRequirement"; which LLM implements that function is an
   implementation detail behind one interface (mirrors the
   `SourceConnector` pattern already used for data sources).
4. **The schema must survive contradictory or partial input**, because
   recruiters give partial input constantly ("Java Developer from product
   companies" has no experience, no location, no explicit skills list).

---

## 3. The `JobRequirement` schema

### 3.1 Core identity

| Field | Type | Status | Purpose |
|---|---|---|---|
| `raw_query` | string | **Required** | The verbatim recruiter input. Always stored, never discarded — it's the audit trail and the fallback if structured extraction fails or needs re-processing with a better model later. |
| `role` | string | **Required** | Normalized job title/function (e.g. "Product Engineer"). Primary key every matching pass starts from. |
| `role_synonyms` | string[] | **AI Derived** | e.g. `role="Backend Developer"` → synonyms `["Backend Engineer", "SDE - Backend"]`. Needed because connectors/sources title things differently than recruiters phrase queries — without this, "Backend Developer" won't find a candidate titled "Backend Engineer" on LinkedIn. |

### 3.2 Experience

| Field | Type | Status | Purpose |
|---|---|---|---|
| `min_experience_yrs` | float \| null | **Optional** | "7+ years" → `7`. Absent when recruiter doesn't mention experience (e.g. "Java Developer from product companies"). Must be optional — forcing a default (like `0`) would silently misrepresent "no preference" as "junior only." |
| `max_experience_yrs` | float \| null | **Optional** | Recruiters do say "3-5 years" or "not more than 10 years." Rare but real; omitting it would drop a real constraint. |
| `experience_qualifier` | enum: `min` \| `max` \| `range` \| `unspecified` | **AI Derived** | Disambiguates whether `min_experience_yrs` alone means "at least" (typical) vs. "exactly" — matters because "7+ years" and "7 years experience" are different constraints. |

### 3.3 Location

| Field | Type | Status | Purpose |
|---|---|---|---|
| `location` | string \| null | **Optional** | e.g. "Bangalore". Absent for remote-first or unspecified searches. |
| `location_type` | enum: `onsite` \| `hybrid` \| `remote` \| `unspecified` | **AI Derived** | Recruiters increasingly say "remote" or "hybrid" instead of a city. Conflating this with `location` would lose the distinction between "must be in Bangalore" and "remote, no location constraint." |
| `open_to_relocation` | boolean \| null | **AI Derived** | Directly from the brief's example: "React Developer willing to relocate." This is a candidate-attribute filter, not a location filter — it changes *how* location scoring works (candidates outside `location` are not excluded, just scored differently), so it must be its own field, not folded into `location_type`. |

### 3.4 Skills

| Field | Type | Status | Purpose |
|---|---|---|---|
| `must_have_skills` | string[] | **AI Derived** | e.g. `["AWS", "Kubernetes"]`. Hard filter — matching engine's primary weight driver. |
| `nice_to_have_skills` | string[] | **AI Derived** | Skills mentioned with hedging language ("familiarity with," "bonus if") — soft filter, scored but not disqualifying. |
| `skill_synonyms` | map<string, string[]> | **AI Derived** | e.g. `"K8s" -> "Kubernetes"`, `"JS" -> "JavaScript"`. Without this, a candidate profile that says "K8s" never matches a query for "Kubernetes." This is what makes `must_have_skills` actually work against real-world resume text. |

### 3.5 Company / industry background

Directly required by two of the seven examples ("from product companies,"
"from FinTech") — this is not a hypothetical need.

| Field | Type | Status | Purpose |
|---|---|---|---|
| `company_type` | enum: `product` \| `service` \| `startup` \| `enterprise` \| `unspecified` | **AI Derived** | "from product companies" is an extremely common recruiter phrase in the Indian tech hiring market this platform targets. Without a dedicated field, this constraint has nowhere to live and gets silently dropped. |
| `industry` | string \| null | **AI Derived** | "FinTech," "Healthcare," "E-commerce." Free-text-but-normalized (see §6) rather than an enum, because the industry list is open-ended and will keep growing — an enum would need a code change every time a recruiter names a new vertical. |
| `target_companies` | string[] | **Optional** | Recruiters sometimes name companies directly ("someone like an ex-Flipkart PM"). Explicit opt-in list, separate from `industry`, because it's a much stronger and more literal signal. |
| `excluded_companies` | string[] | **Optional** | Rarer, but real ("not from a service company," "nobody from our competitor X"). Symmetric to `target_companies` for the same reason — it's a hard exclusion, not a soft de-prioritization, so it can't be represented by a negative weight on `company_type`. |

### 3.6 Availability / urgency

| Field | Type | Status | Purpose |
|---|---|---|---|
| `notice_period` | enum: `immediate` \| `<15_days` \| `<30_days` \| `<60_days` \| `<90_days` \| `unspecified` | **AI Derived** | Directly from "DevOps Engineer with immediate joining." This is a hiring-urgency signal that changes ranking (an otherwise-perfect candidate on a 90-day notice may rank below a good-enough candidate who can start now), so it needs to reach the matching engine as structured data, not stay buried in `raw_query`. |

### 3.7 Compensation (not in the examples, but flagged — see §8)

| Field | Type | Status | Purpose |
|---|---|---|---|
| `budget_min` / `budget_max` | number \| null | **Optional** | Recruiters very frequently think in a comp band even when they don't say so in the first query ("Product Engineer... budget up to 40 LPA"). Not in the brief's seven examples, but omitting it entirely is a real gap — see recommendation in §8. |
| `currency` | string | **Optional**, defaults from recruiter locale | Needed the moment budget fields are populated; India/US/EU recruiters think in different currencies and this platform is explicitly targeting the Indian market (Naukri, iimjobs) alongside global sources (LinkedIn), so this can't be assumed. |

### 3.8 Meta / system fields

| Field | Type | Status | Purpose |
|---|---|---|---|
| `confidence_scores` | map<field_name, float 0-1> | **AI Derived** | Per-field confidence, not one blanket confidence for the whole object. "Bangalore" extracted from an explicit "in Bangalore" should score near 1.0; a `company_type` inferred from indirect phrasing should score lower. Downstream consumers (esp. matching engine, §7) use this to decide whether a constraint is a hard filter or a soft weight. |
| `ambiguous_fields` | string[] | **AI Derived** | Names of fields the model was not confident about, surfaced so the UI can optionally ask the recruiter a clarifying follow-up ("Did you mean strictly Bangalore, or open to remote?") instead of silently guessing wrong. |
| `parser_version` | string | **Required** | Which prompt/schema version produced this object. Necessary the moment the extraction prompt changes — lets you tell "this record is stale, re-run it" apart from "this record used the current logic." |
| `source_model` | string | **Required** | Which LLM produced the object (e.g. `"gemini-2.5-pro"`). Provider-agnostic schema still needs to know, for debugging and for comparing extraction quality across model swaps. |

---

## 4. How the AI should populate each field

The extraction should run as **one LLM call per query**, producing the full
object in a single structured pass (not one call per field — that's slower,
costlier, and loses cross-field context, e.g. "product companies" is easier
to classify correctly when the model also sees "Java Developer" for context).

General population strategy per field, grouped by mechanism:

- **Direct extraction** (`role`, `location`, `min_experience_yrs`,
  `notice_period`): the model pulls these straight from explicit language in
  `raw_query`. High expected confidence.
- **Normalization against a controlled vocabulary**
  (`role_synonyms`, `skill_synonyms`, `company_type`): the model maps free
  text to a known canonical form. This is where a **synonym/taxonomy
  reference table** (maintained outside the LLM, e.g. a `skills_taxonomy`
  lookup) should be supplied to the model as grounding context, rather than
  relying purely on the model's own world knowledge — keeps output stable
  across model swaps and prevents drift (see §9, recommendation 1).
- **Inference from indirect language** (`company_type`, `industry`,
  `open_to_relocation`, `experience_qualifier`): the model has to reason
  about phrasing rather than pattern-match keywords. These fields should
  always carry a `confidence_scores` entry below the "direct extraction"
  fields, because they're inherently softer judgments.
- **Absence is a valid answer.** For every optional field, the prompt must
  explicitly instruct the model to return `null`/empty rather than invent a
  plausible-sounding value. This is the single most important prompting rule
  in the whole engine — an LLM that "fills in" a missing location or
  experience band is worse than one that leaves it blank, because a wrong
  guess silently corrupts every downstream ranking.

---

## 5. Edge cases

| Edge case | Example | How the schema handles it |
|---|---|---|
| No experience mentioned | "Java Developer from product companies" | `min_experience_yrs = null`, not `0`. A `0` would wrongly imply "fresher-friendly." |
| No skills mentioned at all | "Product Manager from FinTech" | `must_have_skills = []`. Matching engine treats an empty required-skills list as "no skill filter," not "candidate must have zero skills." |
| Conflicting signals | "Senior Engineer, 2 years experience" | Both `role` (implies seniority) and `min_experience_yrs` (implies junior) are extracted as-is; conflict is not resolved by the parser. It's surfaced via `ambiguous_fields` and left for the matching engine / recruiter to reconcile — the parser's job is extraction, not judgment calls about what the recruiter "really meant." |
| Multiple locations | "Bangalore or Hyderabad" | `location` becomes a list-capable field in practice — recommend `location` be `string[]` rather than `string` (flagged as a correction to §3.3 in the recommendations, §8). |
| Ambiguous role | "Engineer" alone | `role = "Engineer"`, `role_synonyms = []`, and `ambiguous_fields` includes `"role"` with low confidence — never silently narrowed to a guess like "Software Engineer." |
| Compound/relative experience | "3-5 years" | `min_experience_yrs=3`, `max_experience_yrs=5`, `experience_qualifier="range"`. |
| Slang / abbreviations | "K8s", "GCP", "Immediate joiner" | Resolved via the skills/notice-period taxonomy grounding described in §4, not left to raw model recall. |
| Negation | "not from service companies" | Must populate `excluded_companies`/`company_type` exclusion, not be silently dropped — negation handling should be an explicit test case in the eval suite (§9, recommendation 3). |
| Non-English or code-mixed input (Hinglish) | "Bangalore mein AWS wala Product Engineer chahiye" | Out of scope for v1 but should be a named limitation, not a silent failure — flagged in §8. |
| Empty or garbage query | "" or "asdkj" | The engine must return a valid `JobRequirement` shell with `role=null`, everything else empty, and a top-level `is_valid=false` (see §6) rather than erroring — callers (API layer) decide whether to reject or ask the recruiter to rephrase. |

---

## 6. Validation

Validation has to happen at two layers, because "did the LLM return
well-formed JSON" and "does this JobRequirement make business sense" are
different questions:

1. **Structural validation (schema-level, deterministic, no AI involved).**
   The object must conform to the schema's types — this is standard Pydantic
   validation once implemented: correct types, enums restricted to their
   allowed values, numeric fields non-negative, `max_experience_yrs >=
   min_experience_yrs` when both present. This layer rejects malformed LLM
   output before it ever reaches matching/search — a structurally invalid
   object should trigger one automatic re-prompt attempt, then fall back to
   an "unparsed" state rather than propagate bad data.

2. **Semantic validation (business-rule-level).** Structurally valid but
   nonsensical combinations — e.g. `min_experience_yrs=50`,
   `location_type="remote"` with a non-null `location` and
   `open_to_relocation=false` (contradictory) — should be flagged into
   `ambiguous_fields` rather than hard-rejected. The design principle here:
   structural problems are the parser's fault and should be retried;
   semantic oddities might be exactly what the recruiter meant, so they're
   surfaced, not silently corrected.

3. **Normalization validation.** Every field populated via a controlled
   vocabulary (§4) should be checked against that vocabulary post-extraction.
   If the model returns a skill or company_type value outside the known set,
   that's treated as an extraction issue (logged for taxonomy expansion),
   not silently trusted.

`is_valid: boolean` and `validation_errors: string[]` should be top-level
fields on the object (in addition to the ones in §3.8) so downstream
consumers can check validity without re-deriving it themselves.

---

## 7. How downstream modules consume this object

**Search Engine (source fan-out / connectors dispatch layer)**
Reads `role` + `role_synonyms` to build the query sent to each
`SourceConnector`. Uses `location`/`location_type` to decide whether to
include location as a search parameter to sources that support server-side
location filtering (e.g. a job board's own search API) versus sources that
require post-fetch filtering. Does **not** need `confidence_scores` — the
search layer's job is recall (cast a wide net), not precision.

**Matching Engine**
This is the primary consumer of nearly every field, and the only consumer of
`confidence_scores`. Its scoring logic maps roughly to what's already in
`services/matching_engine.py`, extended:
- `must_have_skills` → hard filter / primary weight (already how
  `_skill_score` works today).
- `nice_to_have_skills` → soft weight bonus, currently absent from the
  matching engine and worth adding once this schema lands.
- `min_experience_yrs` / `max_experience_yrs` / `experience_qualifier` →
  experience scoring (extends today's `_experience_score`).
- `location` / `location_type` / `open_to_relocation` → location scoring
  (extends today's `_location_score`, but should stop hard-zeroing
  out-of-location candidates when `open_to_relocation` context suggests
  relocation is acceptable to the recruiter).
- `company_type` / `industry` / `target_companies` / `excluded_companies` →
  new scoring dimension not present in the matching engine today.
- `notice_period` → new scoring dimension; likely a tie-breaker/urgency
  multiplier rather than a primary weight.
- `confidence_scores` → used to *down-weight* a criterion the parser wasn't
  sure about, so a shaky `company_type` guess doesn't disqualify an
  otherwise-strong candidate as hard as a confident one would.

**Connectors**
Each `SourceConnector.fetch()` receives the `JobRequirement` (or a relevant
subset) as its query input — this is already the shape `fetch(requirement)`
takes in `services/connectors/base.py`. Connectors that talk to source APIs
supporting native filters (title, location, skills) can push filtering
upstream to the source itself; connectors without that capability (e.g. a
resume-upload batch) simply return broad candidate pools and let the
Matching Engine do all filtering. The connector layer never inspects
`company_type`/`industry`/`notice_period` directly today — those stay
purely a Matching Engine concern unless/until a specific source supports
filtering on them.

---

## 8. Gaps / recommended improvements

Flagging these as recommendations only — no schema changes will be made
without approval:

1. **`location` should probably be `string[]` not `string`.** Recruiters
   commonly name multiple acceptable cities ("Bangalore or Hyderabad, or
   remote"). A single-string field forces an artificial pick.
2. **Compensation band (`budget_min`/`budget_max`/`currency`) isn't in the
   seven examples but is a near-certain real-world need** the moment this
   goes in front of actual recruiters. Recommend adding it now rather than
   retrofitting it after the schema is load-bearing in Postgres.
3. **A `skills_taxonomy` / `role_taxonomy` reference dataset is implied
   throughout this doc but doesn't exist yet.** Without it, "K8s" ↔
   "Kubernetes" and "Backend Developer" ↔ "Backend Engineer" normalization
   has no ground truth to check against and will drift every time the
   underlying LLM changes. Recommend this become its own small design task
   before implementation.
4. **An eval set of recruiter queries with hand-labeled correct
   `JobRequirement` output** should exist before implementation, specifically
   covering the edge cases in §5 (especially negation and conflicting
   signals) — otherwise there's no way to know if a prompt change made
   extraction better or worse.
5. **Consider a `seniority_level` enum** (`junior`/`mid`/`senior`/
   `staff`/`principal`), separate from raw years of experience — "Senior
   Engineer, 2 years experience" (an edge case in §5) is exactly the kind of
   query where years-of-experience and stated-seniority diverge, and today's
   schema has no field to capture the stated seniority independent of the
   numeric year count.

---

## 9. Provider-agnostic implementation note (non-binding, for future reference)

Not a decision, just a design constraint to keep in mind for later: the
engine should be a single interface — something like
`QueryUnderstandingEngine.parse(raw_query) -> JobRequirement` — with the
current implementation calling Gemini behind it, mirroring exactly how
`SourceConnector` already isolates LinkedIn/Naukri/ATS specifics behind one
interface. Swapping Gemini for another model later should mean changing one
implementation file, not the schema, the prompt-calling convention across
the codebase, or any downstream consumer.
