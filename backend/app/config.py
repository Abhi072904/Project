import os


class Settings:
    DATABASE_PATH: str = os.environ.get("DATABASE_PATH", "./subsense.db")
    INSIGHT_PROVIDER: str = os.environ.get("INSIGHT_PROVIDER", "mock")  # "mock" | "vertex-ai"
    GCP_PROJECT_ID: str | None = os.environ.get("GCP_PROJECT_ID")
    GCP_LOCATION: str = os.environ.get("GCP_LOCATION", "us-central1")
    UNUSED_SUBSCRIPTION_DAYS: int = int(os.environ.get("UNUSED_SUBSCRIPTION_DAYS", "45"))

    # Signs the session cookie. MUST be set to a long random value in
    # production (e.g. `python3 -c "import secrets; print(secrets.token_hex(32))"`)
    # - anyone who has this value can forge login sessions. Falls back to a
    # fixed dev value locally only so `python3 -m app.main` works out of the box.
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-change-me")

    # True when running behind HTTPS (Render, Vercel, etc.) - controls the
    # Secure flag on the session cookie. Cross-site cookies (frontend and
    # backend on different domains) require Secure + SameSite=None, which
    # only works over HTTPS. Set FLASK_ENV=production (or IS_PRODUCTION=1) in
    # the deployed backend's environment variables.
    IS_PRODUCTION: bool = os.environ.get("IS_PRODUCTION", "0") == "1"


settings = Settings()


def get_insight_provider():
    """Factory - this is the single switch point between mock and production."""
    if settings.INSIGHT_PROVIDER == "vertex-ai":
        from app.insights.vertex_ai_provider import VertexAIProvider

        return VertexAIProvider(project_id=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
    from app.insights.mock_provider import MockProvider

    return MockProvider()
