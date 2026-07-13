-- AlphaSource database schema (Postgres) — target shape, applied via Alembic
-- migrations once corresponding SQLAlchemy models exist under backend/app/models/.
-- Source-agnostic: candidates never reference a specific source directly.

CREATE TABLE sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,              -- e.g. 'linkedin', 'naukri', 'iimjobs', 'ats_greenhouse', 'customer_upload_acme'
    type            TEXT NOT NULL,              -- 'social', 'job_board', 'ats', 'resume_upload'
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    config          JSONB DEFAULT '{}',         -- connector-specific settings, API keys reference, etc.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE candidates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name           TEXT NOT NULL,
    email               TEXT,
    phone               TEXT,
    location            TEXT,
    current_title       TEXT,
    current_company     TEXT,
    total_experience_yrs NUMERIC(4,1),
    skills              TEXT[] NOT NULL DEFAULT '{}',
    summary             TEXT,
    resume_url          TEXT,
    embedding           VECTOR(1536),           -- pgvector, for semantic similarity matching
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Many-to-many: same human found via multiple sources collapses into one candidate row.
CREATE TABLE candidate_source_links (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id        UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    source_id           UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    external_id         TEXT NOT NULL,          -- the ID/URL of this profile within that source
    raw_payload         JSONB,                  -- original unnormalized data, kept for audit/debug
    fetched_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, external_id)
);

CREATE TABLE searches (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recruiter_query     TEXT NOT NULL,           -- raw plain-English input
    parsed_requirement  JSONB NOT NULL,          -- structured JobRequirement produced by the LLM
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE match_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    search_id           UUID NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
    candidate_id        UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    match_score         NUMERIC(5,2) NOT NULL,   -- 0-100
    reasoning           TEXT NOT NULL,           -- human-readable explanation
    rank                INT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (search_id, candidate_id)
);

CREATE INDEX idx_candidates_location ON candidates (location);
CREATE INDEX idx_candidates_skills ON candidates USING GIN (skills);
CREATE INDEX idx_match_results_search ON match_results (search_id, rank);
CREATE INDEX idx_source_links_candidate ON candidate_source_links (candidate_id);
