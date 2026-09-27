"""Interpret a plain-language correction request against a run's line items.

Per the README's product surface: "the accountant can say 'Business Credit
Card should be 2069 not 2068' in plain language; Claude identifies the
specific line item(s), applies the fix live in the preview." This module
only does the identification — turning the message plus the run's current
line items into either one confident (line item, code) match, or a set of
candidates for the accountant to pick from when the request is ambiguous.
Applying the result is the caller's job (same code path as a manual
correction), so this never writes anything itself.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ChatLineItemSummary:
    id: int
    raw_name: str
    ancestors: tuple[str, ...]
    matched_code: str | None


@dataclass(frozen=True)
class ChatCorrectionRequest:
    message: str
    line_items: tuple[ChatLineItemSummary, ...]
    taxonomy: dict[str, str]


@dataclass(frozen=True)
class ChatCorrectionResult:
    line_item_id: int | None
    """Set only when exactly one line item was identified with high
    confidence. None means the request was ambiguous, matched nothing, or
    named a code outside the client's taxonomy — see `candidate_ids` and
    `explanation`."""
    resulting_code: str | None
    candidate_ids: tuple[int, ...]
    """Line items the model considered plausible but couldn't pick between,
    or couldn't fully resolve (e.g. it found the account but the message
    didn't give a valid code). Empty when `line_item_id` is set, or when
    nothing plausible was found at all."""
    explanation: str
    """Model's own account of what it did or why it couldn't, shown to the
    accountant as-is."""


ChatCorrectionInterpreter = Callable[
    [ChatCorrectionRequest], Awaitable[ChatCorrectionResult]
]


SYSTEM_PROMPT = (
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

TOOL_NAME = "report_correction"
TOOL_SCHEMA = {
    "name": TOOL_NAME,
    "description": (
        "Report the result of interpreting the accountant's correction request."
    ),
    "parameters": {
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


def build_user_message(request: ChatCorrectionRequest) -> str:
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



def result_from_payload(
    payload: dict, request: ChatCorrectionRequest
) -> ChatCorrectionResult:
    """Turn a provider's structured response into a result, trusting only
    line item ids and codes that actually exist. Shared by every provider so
    the validation rules can't drift between them."""
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
