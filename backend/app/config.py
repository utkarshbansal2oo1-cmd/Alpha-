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


settings = Settings()
