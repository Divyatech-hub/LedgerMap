"""Provider-neutral LLM classification for unresolved review items.

Per the README's design decision 6: the target taxonomy is a fixed, closed
list per client. The classifier must return either a real code from that
list or an explicit NONE_MATCH — never an invented code — so every response
is validated against the taxonomy before it's trusted. Swapping providers
means writing a new `Classifier` and passing it in; nothing else in the
pipeline should need to change.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

NONE_MATCH = "NONE_MATCH"


@dataclass(frozen=True)
class ClassificationRequest:
    account_name: str
    ancestors: tuple[str, ...]
    """The account's position in the TB hierarchy, root first. For sub-ledger
    detail lines (e.g. a customer name under Accounts Receivable), the name
    alone is meaningless — the ancestor chain is what identifies the account.
    """
    taxonomy: dict[str, str]
    """The client's closed code -> description list. The classifier may only
    return one of these codes, or NONE_MATCH."""


@dataclass(frozen=True)
class ClassificationResult:
    code: str | None
    """None means the model returned NONE_MATCH or an invalid/unparseable
    response — both are treated the same way by the caller: leave the line
    item in review rather than risk assigning a code the model didn't
    actually mean to certify."""
    raw_response: str


Classifier = Callable[[ClassificationRequest], Awaitable[ClassificationResult]]


def validate_classification(code: str | None, taxonomy: dict[str, str]) -> str | None:
    """Enforce the closed-list rule regardless of which provider answered:
    a code that isn't in this client's taxonomy is treated as no match."""
    if code is None or code == NONE_MATCH:
        return None
    return code if code in taxonomy else None
