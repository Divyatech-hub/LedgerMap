"""Anthropic-backed implementation of `ChatCorrectionInterpreter`.

Uses a tool-call (forced) rather than free-text JSON parsing, so the
response shape is guaranteed structurally valid — the only thing left to
validate is whether the model's chosen line item id and code are ones that
actually exist, which happens after this returns.
"""

from ledgermap.integrations.llm.chat_correction import (
    ChatCorrectionRequest,
    ChatCorrectionResult,
)

_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = (
    "An accountant is reviewing a trial balance mapping and describes a "
    "correction in plain language, e.g. 'Business Credit Card should be "
    "2069 not 2068'. You are given the run's current line items (id, "
    "account name, ancestor path, current code) and the client's valid "
    "codes. Identify which line item(s) the message refers to and what "
    "code it should become.\n\n"
    "If exactly one line item clearly matches and the requested code is in "
    "the valid list, report it as a confident match. If more than one line "
    "item could plausibly be meant, or the account is clear but the code "
    "is missing/invalid, report the plausible line items as candidates "
    "instead of guessing. If nothing plausible matches at all, report no "
    "match and no candidates."
)

_TOOL_NAME = "report_correction"
_TOOL_SCHEMA = {
    "name": _TOOL_NAME,
    "description": (
        "Report the result of interpreting the accountant's correction request."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "confident_line_item_id": {
                "type": ["integer", "null"],
                "description": (
                    "The single line item id this request applies to, "
                    "only if unambiguous."
                ),
            },
            "resulting_code": {
                "type": ["string", "null"],
                "description": (
                    "The code to assign, only set alongside confident_line_item_id."
                ),
            },
            "candidate_line_item_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Plausible but not confidently-chosen line item ids.",
            },
            "explanation": {
                "type": "string",
                "description": (
                    "One sentence explaining the result, shown to the accountant."
                ),
            },
        },
        "required": [
            "confident_line_item_id",
            "resulting_code",
            "candidate_line_item_ids",
            "explanation",
        ],
    },
}


def _build_user_message(request: ChatCorrectionRequest) -> str:
    line_item_lines = "\n".join(
        f"id={item.id} | {item.raw_name} | ancestors: "
        f"{' > '.join(item.ancestors) or '(top level)'} | current code: "
        f"{item.matched_code or '(none)'}"
        for item in request.line_items
    )
    taxonomy_lines = "\n".join(
        f"{code}: {description}"
        for code, description in sorted(request.taxonomy.items())
    )
    return (
        f"Accountant's message: {request.message}\n\n"
        f"Line items:\n{line_item_lines}\n\n"
        f"Valid codes:\n{taxonomy_lines}"
    )


async def interpret_chat_correction_with_anthropic(
    request: ChatCorrectionRequest,
) -> ChatCorrectionResult:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()
    response = await client.messages.create(
        model=_MODEL,
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        tools=[_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
        messages=[{"role": "user", "content": _build_user_message(request)}],
    )

    tool_use = next(
        (block for block in response.content if block.type == "tool_use"), None
    )
    if tool_use is None:
        return ChatCorrectionResult(
            line_item_id=None,
            resulting_code=None,
            candidate_ids=(),
            explanation="The model didn't return a usable response.",
        )

    payload = tool_use.input
    valid_ids = {item.id for item in request.line_items}
    confident_id = payload.get("confident_line_item_id")
    resulting_code = payload.get("resulting_code")

    if (
        confident_id in valid_ids
        and resulting_code is not None
        and resulting_code in request.taxonomy
    ):
        return ChatCorrectionResult(
            line_item_id=confident_id,
            resulting_code=resulting_code,
            candidate_ids=(),
            explanation=payload.get("explanation", ""),
        )

    candidate_ids = tuple(
        candidate_id
        for candidate_id in payload.get("candidate_line_item_ids", [])
        if candidate_id in valid_ids
    )
    # A confident id that failed validation (bad code, or hallucinated id)
    # is still a useful candidate rather than being dropped entirely.
    if confident_id in valid_ids and confident_id not in candidate_ids:
        candidate_ids = (confident_id, *candidate_ids)

    return ChatCorrectionResult(
        line_item_id=None,
        resulting_code=None,
        candidate_ids=candidate_ids,
        explanation=payload.get("explanation", ""),
    )
