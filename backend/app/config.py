"""Centralized settings, loaded from environment / .env.

Nothing in the rest of the app should read os.environ directly — import
`settings` from here instead, so every value has one source of truth.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "AlphaSource API"
    ENV: str = "development"

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg2://alphasource:alphasource@localhost:5432/alphasource"

    # --- CORS ---
    # Comma-separated list of allowed origins, e.g. "http://localhost:5173,https://app.alphasource.ai"
    #
    # Sprint 16 fix: the deployed marketing site (https://alphasource.vercel.app)
    # was NOT in this list -- confirmed via a live browser reproduction where
    # the backend correctly returned "Disallowed CORS origin" (400) for that
    # origin. Any real deployment MUST still set CORS_ORIGINS explicitly via
    # its own environment variable to the actual production origin(s) --
    # this default only prevents the exact failure mode observed (a fresh
    # deploy with no CORS_ORIGINS env var set at all falling back to
    # localhost-only and silently blocking the real site).
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:4173,https://alphasource.vercel.app"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # --- AI ---
    GEMINI_API_KEY: str = ""

    # Sprint 29: Query Understanding's LLM provider is now configurable.
    # Gemini's free tier caps at 20 generate_content calls/day, which was
    # getting exhausted from live recruiter testing alone (see
    # docs/TECH_DEBT.md / Sprint 29 notes) -- Groq's free tier gives 1,000
    # requests/day on Llama 3.3 70B at zero cost, so it's the default.
    # GEMINI_API_KEY stays required for GitHub's semantic embedding match
    # (app/integrations/github/intelligence/semantic_matcher.py), which is
    # unrelated to Query Understanding and unaffected by this setting --
    # Groq has no embeddings endpoint, so Gemini remains in the system
    # regardless of QUERY_PROVIDER.
    GROQ_API_KEY: str = ""
    QUERY_PROVIDER: str = "groq"
    FALLBACK_PROVIDER: str = "gemini"

    # Sprint 30: which CandidateRepository implementation
    # get_candidate_repository() returns. Defaults to "memory" -- the
    # original in-memory/JSON-seed behavior every existing test and local
    # dev setup already assumes -- so nothing breaks without a reachable
    # Postgres instance. Set to "postgres" (and ensure DATABASE_URL points
    # at a real database with migrations applied) to persist candidates
    # across restarts/redeploys instead of losing them every time, per the
    # standing gap this sprint closes.
    CANDIDATE_REPOSITORY_BACKEND: str = "memory"

    # Sprint 30: minimal recruiter identity. If set, a recruiter account
    # with this username/password is created automatically on startup
    # (only when the "postgres" repository backend is active and no
    # recruiter exists yet) -- see app/auth/bootstrap.py. Deliberately not
    # a general user-registration flow; this is "just enough" identity for
    # a small team, not enterprise auth.
    ADMIN_USERNAME: str = ""
    ADMIN_PASSWORD: str = ""

    # Sprint 30: how long an issued login session stays valid.
    SESSION_TTL_HOURS: int = 24 * 7

    # Sprint 30: whether protected endpoints (POST /api/search/smart,
    # /integrations/*/configure) actually require a valid session token.
    # Defaults to False so every existing test and local dev setup with no
    # Postgres configured keeps working exactly as before -- flip to True
    # only once ADMIN_USERNAME/ADMIN_PASSWORD and a real Postgres
    # DATABASE_URL are both set, so there's an actual account to log into.
    REQUIRE_AUTH: bool = False

    # Sprint 32: which backend GitHubConfigStore (and, going forward, any
    # other connector's credential store) uses to hold secrets. Defaults
    # to "memory" -- today's exact in-process, wiped-on-restart behavior
    # -- so local dev/tests with no Postgres configured keep working
    # unchanged. Set to "postgres" once DATABASE_URL points at a real,
    # migrated database to persist connector credentials (e.g. the GitHub
    # PAT) across restarts/redeploys instead of losing them every time.
    CONNECTOR_CREDENTIALS_BACKEND: str = "memory"

    # Sprint 32: the symmetric key used to encrypt connector secrets
    # (e.g. the GitHub PAT) before they're written to Postgres -- see
    # app/credentials/crypto.py. Only required when
    # CONNECTOR_CREDENTIALS_BACKEND=postgres; generate one with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # and set it as a Railway environment variable. Never commit a real
    # value of this to source control.
    APP_ENCRYPTION_KEY: str = ""

    # Sprint 34: GitHub discovery used to fetch a single page of Search
    # Users results (capped at GitHubIntelligenceConfig.max_search_results,
    # historically as low as 10) -- a real query like "Java Developer" can
    # match thousands of users, so a one-page fetch silently discarded
    # almost the entire candidate pool. These three settings govern
    # GitHub's OWN native pagination (the documented `page`/`per_page`
    # query params on GET /search/users -- no custom pagination scheme is
    # invented): how many results per page, how many pages to fetch at
    # most, and a hard ceiling on the deduplicated raw pool regardless of
    # how many pages that would take. Defaults (100/5/500) mean a single
    # search can surface up to 500 raw GitHub users before enrichment,
    # filtering, matching, and ranking narrow that down -- a large jump
    # from the old ~10, while still bounded so one search can't run away
    # fetching thousands of profiles/repos/orgs calls.
    GITHUB_SEARCH_PAGE_SIZE: int = 100
    GITHUB_MAX_SEARCH_PAGES: int = 5
    GITHUB_MAX_RAW_CANDIDATES: int = 500

    # Sprint 35: Phase 6 (auto-expand GitHub discovery). discover() stops
    # requesting further GitHub pages as soon as it has collected this many
    # RELEVANT (post-filter) candidates -- not just raw results -- so a
    # recruiter never has to manually re-search just to get more usable
    # profiles. This is independent of GITHUB_MAX_SEARCH_PAGES/
    # GITHUB_MAX_RAW_CANDIDATES, which remain the hard ceilings; this is
    # the "we have enough, stop early" target, usually reached well before
    # those ceilings.
    GITHUB_TARGET_RELEVANT_CANDIDATES: int = 20


settings = Settings()
