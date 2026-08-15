import os


class Settings:
    DATABASE_PATH: str = os.environ.get("DATABASE_PATH", "./subsense.db")
    INSIGHT_PROVIDER: str = os.environ.get("INSIGHT_PROVIDER", "mock")  # "mock" | "vertex-ai"
    GCP_PROJECT_ID: str | None = os.environ.get("GCP_PROJECT_ID")
    GCP_LOCATION: str = os.environ.get("GCP_LOCATION", "us-central1")
    UNUSED_SUBSCRIPTION_DAYS: int = int(os.environ.get("UNUSED_SUBSCRIPTION_DAYS", "45"))


settings = Settings()


def get_insight_provider():
    """Factory - this is the single switch point between mock and production."""
    if settings.INSIGHT_PROVIDER == "vertex-ai":
        from app.insights.vertex_ai_provider import VertexAIProvider

        return VertexAIProvider(project_id=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
    from app.insights.mock_provider import MockProvider

    return MockProvider()
