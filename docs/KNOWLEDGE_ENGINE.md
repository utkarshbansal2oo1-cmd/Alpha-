# Knowledge Engine — Design Document

Status: **Proposal — not implemented.** No code has been written. This
document is a design for review. It introduces a new architectural layer
that sits *before* Query Understanding in the pipeline described in
`docs/ARCHITECTURE.md`, and changes what Query Understanding is responsible
for (extraction of intent only — no synonym generation). That's a real
change to the pipeline in §2 of `ARCHITECTURE.md` and is called out
explicitly in §9 below, pending approval.

---

## 1. Why this exists, and why it's separate from Query Understanding

The previous design doc (`QUERY_UNDERSTANDING_ENGINE.md`) had the LLM doing
two different jobs inside one call: extracting what the recruiter meant
(*"Product Engineer"*, *"AWS"*) and expanding that into searchable
equivalents (*role_synonyms*, *skill_synonyms*). Those are not the same kind
of problem, and conflating them is the core issue this doc fixes:

- **Intent extraction** ("what did the recruiter say") is a language
  understanding problem. It genuinely needs an LLM — recruiter phrasing is
  unbounded and contextual.
- **Synonym/equivalence expansion** ("what else counts as this") is a
  **lookup problem**, not a language problem. "AWS" always expands to the
  same practical skill list (EC2, IAM, Lambda, S3, EKS, CloudFormation)
  regardless of which recruiter typed it, which LLM is running, or what day
  it is. Letting an LLM regenerate this list per-query means:
  - **Non-determinism** — the same query can search for different things on
    different runs, which makes matching results unreproducible and
    unauditable ("why did this candidate show up last time but not now?").
  - **No way to correct a mistake permanently.** If the LLM decides "AWS"
    expands to include "Azure" (wrong), there's no way to fix that except by
    re-prompting and hoping — versus fixing one taxonomy entry once.
  - **No compounding value.** Every query re-derives knowledge from scratch
    instead of building on what the business has already validated. This is
    exactly the asset AlphaSource should be accumulating as IP — hence the
    Knowledge Engine, not the LLM, owns it.

The **Knowledge Engine is a deterministic, versioned, business-owned dataset
plus the lookup/expansion logic around it.** The LLM's role shrinks to
exactly one thing: map recruiter text onto the Knowledge Engine's canonical
vocabulary. It never invents an equivalence relationship.

## 2. Where it sits in the pipeline

Revising the flow from `ARCHITECTURE.md` §2:

```
Recruiter query (plain English)
        │
        ▼
[1] Query Understanding (LLM)
        │  Extracts RAW intent using Knowledge Engine's canonical vocabulary
        │  as grounding context (not synonym generation — see §9)
        │  → JobRequirement with CANONICAL values only
        │    e.g. role="Product Engineer", must_have_skills=["AWS"]
        ▼
[2] Knowledge Engine — Expansion
        │  Canonical values → searchable equivalents
        │  role="Product Engineer" → [Backend Engineer, Platform Engineer,
        │                              Software Engineer, API Engineer]
        │  skill="AWS" → [EC2, IAM, Lambda, S3, EKS, CloudFormation]
        │  → ExpandedJobRequirement (JobRequirement + expansion sets)
        ▼
[3] Source Fan-out ──> SourceConnector[] (parallel)
        ▼
   ... (rest of pipeline unchanged: normalize, dedupe, match, rank, explain)
```

The Knowledge Engine is a new step between Query Understanding and Source
Fan-out. It is also consulted *during* Query Understanding (as read-only
grounding data passed into the LLM prompt, not as a separate call) and
*during* Matching (to check equivalence between a canonical requirement and
a candidate's raw resume text). Three consumers, one dataset — detailed in
§8.

---

## 3. Folder structure

```
backend/
└── app/
    └── knowledge/                         # the Knowledge Engine, as its own module
        ├── __init__.py
        ├── engine.py                      # KnowledgeEngine class: load(), normalize(), expand()
        ├── loader.py                      # reads taxonomy files into memory, validates on load
        ├── models.py                      # dataclasses/Pydantic models for taxonomy entries (in-memory shape)
        ├── versioning.py                  # version resolution, changelog diffing (§7)
        ├── taxonomies/                    # the actual data — this is the IP
        │   ├── roles.json
        │   ├── skills.json
        │   ├── industries.json
        │   ├── company_categories.json
        │   └── _schema/                   # JSON Schema files, one per taxonomy type, for validation
        │       ├── role.schema.json
        │       ├── skill.schema.json
        │       ├── industry.schema.json
        │       └── company_category.schema.json
        └── tests/
            ├── test_normalize.py
            ├── test_expand.py
            └── fixtures/                  # known-input/known-output pairs (the eval set from §7 of the prior doc)
```

Why `taxonomies/` holds flat JSON files rather than living only in Postgres:
taxonomy data is **reference data curated by humans (recruiters/domain
experts), reviewed like code, and versioned like code** — it belongs in git
with diffable pull requests, not in a database table edited through an
admin panel with no review trail. (Postgres does still get a *cache* of the
currently-active version — see §5 — but git is the source of truth.)

`app/knowledge/` is deliberately a peer of `app/services/`, not a submodule
of it. Query Understanding and Matching both depend on Knowledge; Knowledge
depends on neither. This keeps the dependency direction one-way, the same
way `services/connectors/` never depends on `services/matching_engine.py`.

---

## 4. Data model

Every taxonomy entry — regardless of which taxonomy (role, skill, industry,
company category) — shares the same conceptual shape:

| Concept | Description |
|---|---|
| **Canonical value** | The one authoritative name for this concept (e.g. `"Product Engineer"`, `"AWS"`). Everything downstream keys off this string. |
| **Aliases** | Alternative surface forms recruiters/resumes actually use that mean the *same* concept (e.g. `"PE"`, `"Prod Engineer"` → same canonical). Aliases resolve **into** the canonical value — this is the *normalization* direction. |
| **Expansions** | Other canonical values that are *related-but-distinct* concepts worth searching for alongside this one (e.g. `"Product Engineer"` expands to `"Backend Engineer"`, `"Platform Engineer"`, etc.). Expansions do not collapse into one canonical value — this is the *broadening* direction, and it is asymmetric (see below). |
| **Metadata** | `id`, `taxonomy_type`, `status` (`active`/`deprecated`), `created_at`, `updated_at`, `notes` (why this expansion/alias exists — critical for a future editor to know if a mapping was deliberate or a mistake). |

**Aliases vs. Expansions — the distinction that matters most in this whole
design:**
- An **alias** is the *same thing*, different words. `"K8s"` is not a
  related skill to `"Kubernetes"` — it *is* Kubernetes. Alias resolution is
  symmetric and should be a strict many-to-one mapping (many aliases → one
  canonical).
- An **expansion** is a *different but relevant* thing. `"Backend Engineer"`
  is not the same role as `"Product Engineer"`, but a search for one should
  reasonably include the other. Expansion is **directional and not
  necessarily symmetric** — e.g. expanding "Product Engineer" outward to
  "Backend Engineer" is useful for widening a candidate search, but
  expanding "Backend Engineer" should not necessarily pull in every
  "Product Engineer" search, because "Backend Engineer" is the broader/more
  common category. This directionality must be explicit in the data, not
  assumed to be reversible.

This is why aliases and expansions are stored as two separate arrays per
entry rather than one flat "related terms" list — collapsing them would
silently turn "AWS" and "cloud computing skills" into the same kind of
relationship as "AWS" and "Amazon Web Services," which they are not.

### 4.1 Entity-relationship shape (conceptual, pre-implementation)

```
Taxonomy (1) ──has many──> TaxonomyEntry (canonical values)
TaxonomyEntry (1) ──has many──> Alias (strings that normalize TO this entry)
TaxonomyEntry (1) ──has many──> Expansion (→ other TaxonomyEntry, directional, weighted)
```

`Expansion` links two `TaxonomyEntry` rows (possibly across taxonomies —
see §6.1 for cross-taxonomy expansion, e.g. an industry expanding into
relevant company names) rather than being a plain string list, because a
future taxonomy admin tool needs to be able to ask "what expands into
Kubernetes?" (reverse lookup) as easily as "what does Kubernetes expand
into?" — that only works if expansions are real edges between entries, not
one-directional string arrays baked into the source entry only.

---

## 5. JSON taxonomy format

One file per taxonomy type. Proposed shape for `skills.json`:

```json
{
  "taxonomy_type": "skill",
  "version": "2026.07.1",
  "updated_at": "2026-07-08",
  "entries": [
    {
      "id": "skill.aws",
      "canonical": "AWS",
      "aliases": ["Amazon Web Services", "amazon-web-services"],
      "expansions": [
        { "target_id": "skill.ec2", "weight": 0.9, "notes": "core AWS compute service" },
        { "target_id": "skill.iam", "weight": 0.7, "notes": "core AWS access-control service" },
        { "target_id": "skill.lambda", "weight": 0.8, "notes": "common serverless usage of AWS" },
        { "target_id": "skill.s3", "weight": 0.9, "notes": "core AWS storage service" },
        { "target_id": "skill.eks", "weight": 0.75, "notes": "AWS's managed Kubernetes offering" },
        { "target_id": "skill.cloudformation", "weight": 0.6, "notes": "AWS IaC tool" }
      ],
      "status": "active",
      "created_at": "2026-07-01",
      "updated_at": "2026-07-08"
    },
    {
      "id": "skill.ec2",
      "canonical": "EC2",
      "aliases": ["Elastic Compute Cloud"],
      "expansions": [],
      "status": "active",
      "created_at": "2026-07-01",
      "updated_at": "2026-07-01"
    }
  ]
}
```

Same shape for `roles.json`:

```json
{
  "taxonomy_type": "role",
  "version": "2026.07.1",
  "updated_at": "2026-07-08",
  "entries": [
    {
      "id": "role.product_engineer",
      "canonical": "Product Engineer",
      "aliases": ["PE", "Prod Engineer"],
      "expansions": [
        { "target_id": "role.backend_engineer", "weight": 0.8, "notes": "significant overlap in day-to-day responsibilities" },
        { "target_id": "role.platform_engineer", "weight": 0.7, "notes": "" },
        { "target_id": "role.software_engineer", "weight": 0.6, "notes": "broader umbrella term" },
        { "target_id": "role.api_engineer", "weight": 0.65, "notes": "" }
      ],
      "status": "active",
      "created_at": "2026-07-01",
      "updated_at": "2026-07-08"
    }
  ]
}
```

`industries.json` and `company_categories.json` follow the identical
`{id, canonical, aliases, expansions, status, timestamps}` shape — this
uniformity is deliberate (§3: one `models.py` shape serves every taxonomy
type; no taxonomy-specific parsing code).

**Why `weight` on expansions:** not all expansions are equally strong.
"EC2" is core-AWS in a way "CloudFormation" is more peripheral. The Matching
Engine (§8) needs this weight to avoid treating "candidate knows
CloudFormation" as equally strong evidence of AWS proficiency as "candidate
knows EC2." Without weights, expansion silently flattens signal strength.

**Why a JSON Schema per taxonomy type (`_schema/`):** every taxonomy file
must be validated on load and, more importantly, validated by CI *before* a
pull request touching taxonomy data can merge — this is what makes the data
trustworthy as IP. A malformed entry (missing `id`, a dangling
`target_id` that doesn't exist) should fail the build, not fail silently at
runtime three months later when a query happens to touch that entry.

---

## 6. Loading strategy

1. **Source of truth: JSON files in git**, loaded and validated at
   application startup (`app/knowledge/loader.py`), not read from disk
   per-request. All taxonomies are small (thousands of entries, not
   millions) and load entirely into memory as indexed lookup structures:
   - `canonical_by_alias: dict[str, str]` — O(1) alias → canonical
     resolution.
   - `entry_by_id: dict[str, TaxonomyEntry]` — O(1) entry lookup.
   - `expansions_by_id: dict[str, list[Expansion]]` — O(1) expansion lookup.
2. **Validation on load**, not just via CI: every `target_id` referenced in
   an `expansions` array must resolve to a real entry `id` in some loaded
   taxonomy, every `id` must be unique within its taxonomy, and the file
   must conform to its JSON Schema. A failed validation should hard-fail
   application startup — a Knowledge Engine that might be silently
   half-loaded is worse than an application that won't start, given how
   central this becomes to matching quality.
3. **In-memory singleton, not per-request.** The `KnowledgeEngine` instance
   is constructed once (analogous to how `services/connectors/registry.py`
   builds its connector list once) and reused across requests — reloading
   JSON per API call would be pure waste for data that changes on a release
   cadence, not per-request.
4. **A Postgres-backed read cache is a deliberate future addition, not part
   of v1 loading**, for one specific reason: once a taxonomy admin UI exists
   (mentioned in §8 of the prior design doc as a recommendation), edits made
   through that UI need a place to live before they're promoted back into
   the git-tracked JSON via a reviewed PR. That flow is out of scope for
   this initial design — v1 loading is git JSON → memory, full stop.
5. **Hot-reload in development only** (e.g. a file-watcher that reloads
   `KnowledgeEngine` when taxonomy JSON changes locally), never in
   production — production always loads once at startup and requires a
   deploy to pick up a new taxonomy version, so that "which taxonomy version
   served this request" is always answerable from the deployed build, not
   from a mutable runtime state.

---

## 7. Versioning strategy

Every taxonomy file carries its own `version` string (`"2026.07.1"` —
`YYYY.MM.patch`), independent of the others — the skills taxonomy and the
role taxonomy will not always change at the same time, and forcing one
version number across all four taxonomies would mean every alias fix to
`skills.json` bumps a version number that has nothing to do with roles.

Versioning has three jobs:

1. **Reproducibility.** Every `JobRequirement` produced by Query
   Understanding should record which taxonomy versions were active when it
   was expanded (a small addition to the meta fields already proposed in
   `QUERY_UNDERSTANDING_ENGINE.md` §3.8 — e.g.
   `knowledge_versions: {"skill": "2026.07.1", "role": "2026.07.1", ...}`).
   This means a search result can always be explained: "this candidate
   matched because 'AWS' expanded to include 'EKS' under skills taxonomy
   version 2026.07.1" — and if that expansion is later corrected, old
   results remain explainable rather than retroactively confusing.
2. **Safe rollback.** If a taxonomy edit (e.g. someone adds a bad expansion)
   degrades match quality, the fix is reverting to the previous JSON version
   in git and redeploying — no data migration, no code change, because the
   taxonomy is a versioned artifact, not mutable state.
3. **Changelog as a first-class output**, not an afterthought:
   `versioning.py` should be able to diff two versions of the same taxonomy
   file and produce a human-readable changelog ("added alias 'K8s' →
   Kubernetes; added expansion Product Engineer → API Engineer, weight
   0.65"). This is what makes taxonomy changes reviewable in a pull request
   the same way code changes are — a raw JSON diff of a 2,000-entry file is
   not reviewable; a generated changelog is.

Deprecation, not deletion: an entry that's no longer accurate gets
`"status": "deprecated"` rather than being removed from the file. Historical
`JobRequirement` records may reference an `id` that's since been deprecated,
and the loader must still be able to resolve it (deprecated entries stay in
the lookup maps, just excluded from *new* expansion suggestions) — otherwise
old search results become unexplainable, which defeats the entire point of
§7.1.

---

## 8. How Query Understanding and Matching Engine consume it

**Query Understanding (revised responsibility from the prior design doc):**
The LLM prompt includes a relevant slice of canonical vocabulary as grounding
context — not the entire taxonomy (too large, wasteful), but a targeted
subset. In practice this means the Knowledge Engine exposes a
**fuzzy-match/candidate-lookup function** (`suggest_canonical(raw_term) ->
list[TaxonomyEntry]`, using string similarity against `canonical` values and
`aliases`) that narrows a huge taxonomy down to a handful of plausible
candidates for a given raw term, which then get passed into the LLM prompt so
the model can pick the correct one from real options rather than
free-generating a canonical value from its own training data. The LLM's only
output for any skill/role/industry/company-type field is: *which existing
canonical id best matches what the recruiter said* (or "none of these,
flag as unrecognized" — see below). It never writes a synonym or expansion
itself.

**Handling terms the taxonomy doesn't yet know about:** when
`suggest_canonical` returns no good match, the term is recorded as an
**unresolved term** (logged, not silently dropped and not guessed by the
LLM) — this becomes the intake queue for taxonomy maintainers to review and
add as a new alias or new entry. This is the mechanism referenced in §9
("how future taxonomies/terms get added") and is what lets the taxonomy grow
from real usage instead of requiring maintainers to anticipate every term in
advance.

**Matching Engine:** consumes the *expanded* requirement (`role` +
`role_synonyms`/expansions, `must_have_skills` + their expansions), and this
is where expansion `weight` (§5) becomes a scoring input — a candidate whose
resume mentions "EC2" and "S3" (weight 0.9 each) should score higher on AWS
proficiency than one who only mentions "CloudFormation" (weight 0.6), even
though both technically "match AWS" under naive keyword expansion. The
Matching Engine also uses the *alias* direction when scanning a candidate's
raw skills list — a candidate profile listing "K8s" must resolve to
"Kubernetes" via the same alias table before scoring, so normalization is
symmetric across both the recruiter-query side and the candidate-profile
side of the match.

**Connectors:** not a direct consumer in this design. Connectors receive the
already-expanded search terms from the pipeline (§2, step 3) as plain
strings — they don't need to know these strings came from taxonomy
expansion versus being typed directly. This keeps the Knowledge Engine
invisible to the connector interface, preserving the existing
`SourceConnector.fetch(requirement)` contract without any change to
`services/connectors/base.py`.

---

## 9. How future taxonomies will be added

Adding a **new taxonomy type** entirely (e.g. a future "certifications"
taxonomy, or "tools" separate from "skills"):
1. Add one new JSON file under `taxonomies/` following the same
   `{id, canonical, aliases, expansions, status, timestamps}` shape.
2. Add its JSON Schema under `taxonomies/_schema/`.
3. Register it in `loader.py`'s list of taxonomies to load at startup — this
   should be a one-line addition (a registry pattern, deliberately mirroring
   `services/connectors/registry.py`'s "one new line" philosophy already
   established in this codebase) — not a change to `engine.py`'s
   normalize/expand logic, which is taxonomy-agnostic by construction.
4. No changes to Query Understanding or Matching Engine code are needed
   purely to *support* a new taxonomy type existing — they only change when
   they start *consuming* the new type for a specific field (e.g. a
   `certifications` field would need to be added to `JobRequirement` first,
   which is a schema change subject to the same approval process as
   everything else in this document).

Adding a **new entry to an existing taxonomy** (the common case — new
alias, new expansion, brand-new skill/role):
1. Edit the relevant JSON file directly (git PR).
2. CI runs schema validation + the changelog diff (§7) as part of review.
3. Bump that taxonomy's version string.
4. No code deploy is strictly required for data-only changes if the loader
   reads from a released/tagged data path — but per §6.5, production always
   requires a redeploy to pick up new taxonomy data, by design, so that the
   active taxonomy version is always tied to a specific deployed build.

This is the same operational model as the existing "add a new data source"
pattern in `ARCHITECTURE.md` §4 — one additive change, isolated, without
touching the engine that consumes it.

---

## 10. Explicit call-out: this changes the previous design

Per the instruction to flag rather than silently implement architecture
changes: adopting this Knowledge Engine means `QUERY_UNDERSTANDING_ENGINE.md`
needs two edits when both designs are eventually approved together:
- §4 ("How the AI should populate every field") for `role_synonyms` and
  `skill_synonyms` needs to change from "the model infers synonyms" to "the
  model selects a canonical id via Knowledge Engine grounding; the Knowledge
  Engine performs the actual expansion as a separate pipeline step" (§2 of
  this doc).
- The pipeline diagram in `ARCHITECTURE.md` §2 gains a new step between
  Query Understanding and Source Fan-out.

No changes have been made to either file. Flagging both here for approval
alongside this new document, as instructed.
