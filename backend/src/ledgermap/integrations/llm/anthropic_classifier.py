"""Anthropic-backed implementation of the `Classifier` protocol.

Swappable: nothing outside this module knows or cares that Claude is doing
the classification. Per the README's cost note, expected volume is well
under 500 calls/month across all clients, so provider choice here is about
quality and simplicity, not price.
"""

from ledgermap.integrations.llm.classifier import (
    NONE_MATCH,
    ClassificationRequest,
    ClassificationResult,
    validate_classification,
)

_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = (
    "You classify trial balance accounts into a fixed chart of accounts for "
    "an accounting firm. You are given one account's name and its position "
    "in the trial balance hierarchy (its ancestor groups, root first), plus "
    "the client's complete list of valid codes and descriptions. "
    "Respond with ONLY the matching code, exactly as given, or the literal "
    f"text {NONE_MATCH} if nothing in the list genuinely fits. Never invent "
    "a code that isn't in the list. For a sub-ledger detail line (e.g. a "
    "customer or supplier name), classify by what the ancestor chain "
    "represents (receivables, payables, etc.), not by the name itself."
)


def _build_user_message(request: ClassificationRequest) -> str:
    taxonomy_lines = "\n".join(
        f"{code}: {description}"
        for code, description in sorted(request.taxonomy.items())
    )
    ancestor_path = (
        " > ".join(request.ancestors) if request.ancestors else "(top level)"
    )
    return (
        f"Account name: {request.account_name}\n"
        f"Ancestor path: {ancestor_path}\n\n"
        f"Valid codes:\n{taxonomy_lines}"
    )


async def classify_with_anthropic(
    request: ClassificationRequest,
) -> ClassificationResult:
    # Imported lazily so the `anthropic` package is only required when this
    # specific provider is actually used.
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()
    response = await client.messages.create(
        model=_MODEL,
        max_tokens=32,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_message(request)}],
    )
    raw_text = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()
    code = validate_classification(raw_text, request.taxonomy)
    return ClassificationResult(code=code, raw_response=raw_text)
