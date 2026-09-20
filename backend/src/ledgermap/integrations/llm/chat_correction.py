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
