"""Gemini-backed implementation of the `Classifier` protocol."""

from ledgermap.config import get_settings
from ledgermap.integrations.llm.classifier import (
    SYSTEM_PROMPT,
    ClassificationRequest,
    ClassificationResult,
    build_user_message,
    validate_classification,
)
from ledgermap.integrations.llm.gemini_client import get_gemini_client


async def classify_with_gemini(
    request: ClassificationRequest,
) -> ClassificationResult:
    from google.genai import types

    response = await get_gemini_client().aio.models.generate_content(
        model=get_settings().gemini_model,
        contents=build_user_message(request),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            # Picking one code from a closed list needs no reasoning, and
            # thinking tokens would count against the tiny output budget.
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL
            ),
            max_output_tokens=64,
            # We read the structured answer ourselves; the SDK shouldn't try
            # to execute anything on our behalf.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        ),
    )
    raw_text = (response.text or "").strip()
    code = validate_classification(raw_text, request.taxonomy)
    return ClassificationResult(code=code, raw_response=raw_text)
