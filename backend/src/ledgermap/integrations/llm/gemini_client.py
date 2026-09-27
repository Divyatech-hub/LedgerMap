"""Shared Gemini client, authenticated through Google Cloud rather than an
API key.

`enterprise=True` routes calls to the Gemini Enterprise Agent Platform
(previously Vertex AI) inside our own GCP project. Credentials come from
Application Default Credentials: the attached service account when running on
Cloud Run, or `gcloud auth application-default login` on a laptop. Nothing
secret is stored in `.env`, and usage is billed and monitored in the same
project as the rest of the app.
"""

from functools import lru_cache
from typing import TYPE_CHECKING

from ledgermap.config import get_settings

if TYPE_CHECKING:
    from google import genai


@lru_cache
def get_gemini_client() -> "genai.Client":
    # Imported lazily so `google-genai` is only required when this provider
    # is actually used.
    from google import genai

    settings = get_settings()
    return genai.Client(
        enterprise=True,
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
    )
