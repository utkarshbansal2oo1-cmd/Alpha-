# GitHub Connector — Live Validation & Fix (Sprint 20E)

This is not an architecture doc. It is the evidence record for a real bug, found and fixed against the live, deployed application and GitHub's real REST API — no mocks, no simulated success.

## What was tested

The live Railway backend (`https://alpha-production-22c6.up.railway.app`), which already has a real GitHub Personal Access Token configured (`GET /connectors` shows `"github"` with `"status":"connected"`, `"health":{"available":true}`). Six real recruiter queries were POSTed to `/api/search/smart` from an authenticated browser tab (not curl/Python — this sandbox cannot reach `api.github.com` or Railway directly, only the Chrome extension and `web_fetch` can):

| # | Query | Skills Query Understanding extracted | GitHub candidates found (before fix) |
|---|---|---|---|
| 1 | Senior Golang Developer | `["Golang"]` | **0** |
| 2 | Senior React Developer | `["React"]` | **0** |
| 3 | Senior Java Spring Boot Engineer | `["Java", "Spring Boot"]` | 10 (worked — coincidence, see below) |
| 4 | DevOps Kubernetes AWS | `["Kubernetes", "AWS"]` | **0** |
| 5 | AI Engineer LangChain | `["LangChain"]` | **0** |
| 6 | Machine Learning Engineer PyTorch | `["PyTorch"]` | **0** |

5 of 6 real recruiter queries returned zero GitHub candidates from production, before this fix.

## Where candidates disappeared — proven with real API responses

Trace for query #1, "Senior Golang Developer":

```
Recruiter Query: "Senior Golang Developer"
      |
Query Understanding -> role="Senior Golang Developer", skills=["Golang"]
      |
GitHub connector builds search query (Sprint 20B logic, still deployed):
  GET https://api.github.com/search/users?q=Senior+Golang+Developer+Golang+type:user
      |
      v  (tested live, unauthenticated, via web_fetch)
  total_count: 189   <-- GitHub's search DID find real users
      |
  First real result: login "evt"
      |
GET https://api.github.com/users/evt/repos
      |
      v (tested live)
  10 repos returned, including:
    name="toptal-home-assignment", language="Go",
    description="Toptal home assignment for Senior Golang Engineer"
    <-- a genuine Go developer
      |
Candidate filter (pre-fix): infer_languages(repos) -> {"Go"}
  requirement_skills = {"golang"}
  {"golang"} & {"go"}  ==  {}   <-- NO OVERLAP. Candidate DROPPED.
      |
Returned: 0
```

Root cause: the pre-fix filter in `app/discovery/connectors/github_connector.py`'s `discover()` compared the recruiter's skill token only against `infer_languages(repos)` — GitHub's own repo `language` classification (Go, Python, Java, JavaScript, ...). This works only when the skill token happens to be spelled identically to a GitHub language name. It fails for:

- **Spelling mismatches**: "Golang" (recruiter/query term) vs. "Go" (GitHub's actual language label) — same technology, different string.
- **Frameworks and platforms that are never a repo `language` at all**: "React" (a JavaScript library — the repo's language is still JavaScript/TypeScript), "Kubernetes"/"AWS" (infrastructure, not a programming language), "LangChain"/"PyTorch" (Python libraries).

Query #3 ("Java") only worked by coincidence — "Java" is both the recruiter's skill token and GitHub's literal language name for that repo.

This is why 5 of 6 real, common recruiter queries returned nothing: the filter was structurally incapable of recognizing the majority of real skills recruiters actually ask for, regardless of how good GitHub's own search results were.

## The fix

`app/discovery/connectors/github_connector.py`:

1. **Alias table** (`_LANGUAGE_ALIASES`) — a small, explicit, auditable dict mapping common recruiter spellings to GitHub's own language names (`"golang" -> "go"`, `"nodejs"/"node" -> "javascript"`, etc.). Both the requirement skill and GitHub's language are expanded through this table before comparison.
2. **Evidence broadened from "language only" to "language OR real evidence-based skill extraction"** — the connector now also runs `SkillExtractor` (already built in Sprint 20D for enrichment metadata, now also consulted for the filter decision) against each candidate's repo topics, repo names, and descriptions. `SkillExtractor` never hallucinates: a skill is only counted if a literal keyword match exists in real API data.
3. **Two skills added to `SkillExtractor.SKILL_KEYWORDS`**: `"React"` and `"PyTorch"` — both real, evidence-checkable (via topics/repo name/description), previously missing from the table entirely.
4. **Full execution trace logging** (`logger.info("github.discover.trace", ...)`) on every `discover()` call: search query used, users found, profiles fetched, profile-fetch failures, candidates filtered out for lacking skill evidence, and candidates returned — so a future zero-candidate result is always explainable from logs, never silent.

No new connector, engine, registry, or abstraction was introduced. The fix reuses `SkillExtractor`, a module that already existed from Sprint 20D.

## Proof the fix is correct (local, mocked — not claimed as live proof on its own)

Four new regression tests in `app/discovery/connectors/tests_github_connector.py` reproduce the exact failure scenarios found live and confirm each is now fixed:

- `test_discover_matches_golang_requirement_against_go_language_repo` — the exact "evt" / "toptal-home-assignment" case above.
- `test_discover_matches_react_requirement_via_topic_evidence_not_language`
- `test_discover_matches_pytorch_requirement_via_description_evidence`
- `test_discover_still_filters_out_candidates_with_zero_evidence_after_fix` — confirms the broadened filter is not a rubber stamp; a candidate with genuinely no matching evidence is still excluded.

Full suite: 305/305 passing (301 pre-existing + 4 new). This is evidence the fix's *logic* is correct against realistic data — it is explicitly **not** presented as proof that the live application now returns candidates, per the standing requirement that only a live re-test of the deployed app counts as that proof.

## What still has to happen for live proof

This fix lives only in the local backend directory right now. The deployed Railway backend still has the pre-fix code (confirmed live above: 5/6 queries return 0). Local git history in this environment is broken (`No commits yet` on `git status`, unlink permission errors) and, per standing instructions, this assistant does not push code or request GitHub credentials. To get the fix live:

```
cd "path/to/My tool of sourcing/alphasource"
rm -rf .git
git init
git remote add origin https://github.com/utkarshbansal2oo1-cmd/Alpha-.git
git fetch origin
git checkout -b main origin/main
git add .
git commit -m "Sprint 20E: fix GitHub connector skill-matching filter (Golang/React/Kubernetes/AWS/LangChain/PyTorch were silently dropping every real candidate)"
git push origin main
```

Once Railway redeploys, the exact same six live queries can be re-run against `POST /api/search/smart` (the test script is already saved in an open browser tab as `window.__runQuery`) to produce the actual before/after live proof this task requires.

## Sprint 20F: removing dependency on any fixed technology list

Sprint 20E's fix (above) still gated candidates against a fixed ~20-item skill keyword table. That would have failed identically for any query outside that list — "SAP ABAP Consultant," "Snowflake Data Engineer," "ASIC Verification Engineer," "Quantum Computing Researcher" would all have returned zero candidates again, for the same structural reason as Golang/React/PyTorch did.

### The fix

`app/discovery/connectors/github_connector.py`'s candidate filter no longer consults any fixed technology table at all. It now:

1. Tokenizes the recruiter's own query text (`requirement.role` + `requirement.skills`) into lowercase words, stripping only a small, closed set of generic English recruiting/seniority words ("senior," "engineer," "consultant," "with," "and," ...) that carry no technology signal. This stoplist never needs an entry added for a new skill — it only ever contains English job-title grammar, not technology names.
2. Concatenates every real GitHub-supplied text field for a candidate's repos (name, language, description, topics) into one evidence blob.
3. A candidate passes if and only if at least one of the recruiter's own query words appears literally in that evidence blob.

There is no list to be missing an entry from. `test_discover_matches_a_job_title_never_seen_before_with_no_code_changes` proves this directly: it searches for "SAP ABAP Consultant" / skill "ABAP" — a job title and technology that appear nowhere in this codebase, in any table, anywhere — and the candidate is still correctly matched, because "abap" is a literal word in that recruiter query and also a literal word in the candidate's real repo topics/description.

### Codebase audit: every remaining fixed list, and why each is or isn't a discovery-blocking risk

| Location | What it is | Blocks discovery of novel queries? |
|---|---|---|
| `app/discovery/connectors/github_connector.py` (pre-20F) | Candidate skill filter | **Was the actual bug. Fixed in 20F — now zero fixed lists.** |
| `app/query_understanding/` (Gemini-backed) | Understands the recruiter's free-text query | No fixed list at all — genuinely LLM-based, confirmed dynamic by the live trace itself (it correctly extracted `skills=["Golang"]`, `["ABAP"]`-style novel terms with no code involved). |
| `app/knowledge/taxonomies/{roles,skills}.json` (Knowledge Engine) | Canonical role/skill taxonomy, used for enrichment/weighting | No — confirmed via the live `/api/search/smart` response: an unrecognized term (e.g. "Golang") still appears in `search_plan.unresolved` **and** in `search_plan.search_terms`, i.e. it still flows through to search. This taxonomy enriches known terms; it never withholds an unknown one. Frozen this sprint per explicit instruction, and verified not to be the source of the discovery bug. |
| `app/discovery/query_translation/strategies/github.py` `SKILL_TO_GITHUB_TERMS` | Generates extra GitHub search-query variants (e.g. "golang" -> "golang", "language:Go") | No — already has an honest dynamic fallback: an unmapped token falls back to the recruiter's own raw role words (confidence drops to 0.5, nothing is rejected). Not currently deployed to production at all (production still runs the single-literal-query path). Left unchanged this sprint — it degrades gracefully already and isn't on the live path. |
| `app/integrations/github/intelligence/skill_extractor.py` `SKILL_KEYWORDS` | Populates the human-readable `skills_inferred` enrichment display field | No longer a gate as of Sprint 20F (it was never wired to reject candidates in the first place; only `github_connector.py`'s filter was). A candidate with a real but unlisted skill (e.g. ABAP) is still discovered, imported, and stored — it just won't get a pretty canonical label in that one cosmetic field. Left as-is; expanding it is optional future polish, not a correctness bug. |
| `app/services/query_parser.py` `_KNOWN_SKILLS` | Feeds the legacy `/api/v1/search` endpoint (pre-Sprint-13 MVP pipeline) | No — this endpoint is a separate, older code path that never calls the GitHub connector or the Discovery Engine at all. Confirmed via `grep`: only `app/services/pipeline.py` imports it. Not touched. |
| `app/candidate_repository/data/candidates.json` | The Candidate Repository's persistent bootstrap dataset (8 records, pre-dates the Discovery Engine) | No — this is the system's actual data store, not demo-only filler that discovery depends on. It is unrelated to whether GitHub discovery finds candidates for a novel job title; removing it would only start the repository empty. Left unchanged. |

No demo-only or seed-only code paths were found gating GitHub discovery specifically. The one real bug — the connector's candidate filter — is fixed.

### Regression

307/307 tests passing (301 prior + 4 from Sprint 20E + 2 new from Sprint 20F: the never-before-seen-job-title proof, and a check that generic role-noise words don't cause false-positive matches).

### Still required for live proof

Same as Sprint 20E: this fix exists only in the local backend directory. Production still runs the pre-20F code. Use the git commands above once more (same commit target) to deploy, then arbitrary live queries can be tested directly against the deployed app with zero code changes between them, per the actual success criteria.

## Sprint 20G: semantic evidence matching (embeddings), not literal word overlap

Sprint 20F's fix removed all fixed technology lists, but it still required an exact shared word between the recruiter's query and the candidate's evidence. That structurally cannot recognize that "Computer Vision" and a repo about "YOLO, OpenCV, Detectron2" describe the same thing — none of those words overlap at all. The same gap applies to "Cloud Security" <-> "Vault, IAM, OIDC, OAuth2" and "Distributed Systems" <-> "Raft, Paxos, ZooKeeper."

### The fix

New module `app/integrations/github/intelligence/semantic_matcher.py`:

- `GeminiEmbeddingClient` embeds arbitrary text into a vector using Gemini's `text-embedding-004` model, via the same `google-genai` SDK and `GEMINI_API_KEY` already configured for Query Understanding — one already-configured credential, reused, not a new integration to set up.
- `SemanticEvidenceMatcher.is_relevant(requirement_text, evidence_text)` embeds both the recruiter's requirement text and the candidate's real GitHub evidence text (repo name/language/description/topics — unchanged from Sprint 20F, still 100% real API data, nothing fabricated), and compares them by cosine similarity against a threshold.
- The embedding model itself has no knowledge of this product's skills or roles — it was trained to map arbitrary text to arbitrary text. It requires zero maintenance as new job titles or technologies appear, which is what makes this different from every fixed-list approach in Sprints 20D–20F.
- `app/discovery/connectors/github_connector.py`'s filter now tries semantic comparison **first**. If the embedding API is unavailable (no key, network failure, quota, anything) it raises `EmbeddingUnavailableError`, which the connector catches and falls back to Sprint 20F's literal-token evidence match — availability must never depend on one remote call succeeding.

### Proof

11 new tests in `tests_semantic_matcher.py` (cosine similarity math, threshold behavior, the exact "zero-shared-words-but-relevant" case via a fake embedding client, `GeminiEmbeddingClient`'s unavailable/failure wrapping) plus 3 new tests in `tests_github_connector.py`:

- `test_discover_uses_semantic_matcher_to_match_candidate_with_no_shared_words` — the literal "Computer Vision" / "YOLO OpenCV Detectron2" case, with an injected fake matcher standing in for the real embedding model (same reasoning as every other test in this suite: real network calls are never required to run tests).
- `test_discover_semantic_matcher_rejects_irrelevant_candidate`
- `test_discover_falls_back_to_token_match_when_semantic_matcher_unavailable` — proves the connector still returns a real match via Sprint 20F's fallback when the embedding API can't be reached, rather than returning nothing.

Full suite: 321/321 passing (307 prior + 14 new).

### What this does NOT prove yet

The fake-matcher tests above prove the *wiring* is correct — that discover() correctly asks a semantic matcher, correctly falls back on failure, and correctly returns/rejects candidates by its verdict. They do not prove the *real* Gemini embedding model actually places "Computer Vision" and "YOLO/OpenCV" close together in practice — that requires a real embedding API call, which this sandbox cannot make (no outbound network to `generativelanguage.googleapis.com` from this environment, confirmed the same way `api.github.com` was found unreachable in Sprint 20C). Production already has `GEMINI_API_KEY` configured (Query Understanding depends on it and works live), so once this fix is deployed, semantic matching will run for real — but that, too, is part of the live proof still pending your deployment, same as every fix in this document.

### Threshold tuning note

`DEFAULT_SIMILARITY_THRESHOLD = 0.5` is a starting point chosen to favor recall (better to surface one borderline candidate a recruiter can dismiss than silently drop a real one). Once this runs live, the `github.semantic_match` log line records every actual similarity score computed — real production data is the right basis for tuning this number, not a guess made without it.
