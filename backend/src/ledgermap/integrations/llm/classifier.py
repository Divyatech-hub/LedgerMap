"""Provider-neutral LLM classification for unresolved review items.

Per the README's design decision 6: the target taxonomy is a fixed, closed
list per client. The classifier must return either a real code from that
list or an explicit NONE_MATCH — never an invented code — so every response
is validated against the taxonomy before it's trusted. The prompt lives here
rather than in the provider module so swapping providers means writing a new
`Classifier` that sends it; nothing else in the pipeline should need to change.
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


SYSTEM_PROMPT = (
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


def build_user_message(request: ClassificationRequest) -> str:
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
