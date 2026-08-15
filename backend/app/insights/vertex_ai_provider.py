"""
Vertex AI-backed insight provider.

Production implementation. Requires:
  pip install google-cloud-aiplatform
  gcloud auth application-default login   (or a service account key)
  env vars: GCP_PROJECT_ID, GCP_LOCATION (defaults to "us-central1")

This calls Gemini with a structured-JSON system prompt so the response can be
parsed directly into GeneratedInsight objects, the same "constrain the model
to return only JSON, parse, validate" pattern used for structured outputs
against the Claude API elsewhere in this project's ecosystem.

NOTE: this file is written to run for real against Vertex AI in a deployed
environment. It was developed and unit-tested against MockProvider (see
mock_provider.py) because the build sandbox has no outbound network access -
swap INSIGHT_PROVIDER=vertex-ai in config once real GCP credentials are
available and this class takes over with zero code changes elsewhere.
"""
import json
import os

from app.insights.provider import (
    InsightProvider,
    SpendingContext,
    GeneratedInsight,
    InsightBatch,
)

_SYSTEM_PROMPT = """You are a blunt, helpful personal-finance auditor. You are given a
user's recurring subscriptions and spending summary. Return ONLY valid JSON (no markdown
fences, no preamble) matching this schema:

{
  "insights": [
    {
      "insight_type": "unused_subscription" | "trend" | "anomaly" | "summary",
      "headline": "<one short sentence, <= 12 words>",
      "body": "<1-2 sentences, concrete and specific, no fluff>",
      "potential_monthly_savings": <number, 0 if not applicable>,
      "subscription_name": "<name or null>"
    }
  ]
}

Rules:
- Prioritize subscriptions unused 45+ days - those are the highest-value flags.
- Be specific with dollar amounts and day counts. Never say "consider reviewing" -
  say what to do.
- Generate at most 5 insights, ranked by potential_monthly_savings descending.
- If nothing stands out, return a single encouraging "summary" insight instead of
  inventing problems.
"""


def _build_user_prompt(context: SpendingContext) -> str:
    sub_lines = []
    for s in context.subscriptions:
        unused = (
            f"{s.days_since_last_use} days since last use"
            if s.days_since_last_use is not None
            else "no usage data logged"
        )
        sub_lines.append(
            f"- {s.display_name}: ${s.amount:.2f}/{s.cadence} "
            f"(${s.annualized_cost:.2f}/yr, category: {s.category}, {unused})"
        )

    trend = ""
    if context.total_monthly_recurring_prior_period is not None:
        delta = context.total_monthly_recurring - context.total_monthly_recurring_prior_period
        trend = f"\nPrior period recurring total: ${context.total_monthly_recurring_prior_period:.2f} (delta: {delta:+.2f})"

    category_lines = "\n".join(f"  - {c}: ${v:.2f}" for c, v in context.spend_by_category.items())

    return f"""Subscriptions detected:
{chr(10).join(sub_lines)}

Total monthly recurring spend: ${context.total_monthly_recurring:.2f}{trend}

Spend by category ({context.period_label}):
{category_lines}
"""


class VertexAIProvider(InsightProvider):
    name = "vertex-ai"

    def __init__(self, project_id: str | None = None, location: str | None = None, model: str = "gemini-2.0-flash"):
        self.project_id = project_id or os.environ.get("GCP_PROJECT_ID")
        self.location = location or os.environ.get("GCP_LOCATION", "us-central1")
        self.model_name = model
        self._model = None  # lazy-init so import doesn't require credentials

    def _get_model(self):
        if self._model is None:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            if not self.project_id:
                raise RuntimeError(
                    "GCP_PROJECT_ID is not set - VertexAIProvider needs a project to initialize."
                )
            vertexai.init(project=self.project_id, location=self.location)
            self._model = GenerativeModel(self.model_name, system_instruction=_SYSTEM_PROMPT)
        return self._model

    def generate_insights(self, context: SpendingContext) -> InsightBatch:
        model = self._get_model()
        prompt = _build_user_prompt(context)

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.4,
                "response_mime_type": "application/json",
            },
        )

        payload = json.loads(response.text)
        insights = [
            GeneratedInsight(
                insight_type=item["insight_type"],
                headline=item["headline"],
                body=item["body"],
                potential_monthly_savings=float(item.get("potential_monthly_savings") or 0),
                subscription_name=item.get("subscription_name"),
            )
            for item in payload.get("insights", [])
        ]
        return InsightBatch(insights=insights, provider_name=self.name)
