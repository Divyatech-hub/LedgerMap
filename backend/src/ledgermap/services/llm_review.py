"""Optional post-processing step: send still-unresolved line items to an LLM
classifier before they're persisted to the review queue.

Kept separate from `process_workbook` (which stays synchronous, no I/O)
since this step is async, optional, and needs the client's taxonomy — none
of which the pure matching pipeline needs to know about.
"""

from ledgermap.domain.models import MappingCandidate, MappingMethod
from ledgermap.integrations.llm.classifier import ClassificationRequest, Classifier
from ledgermap.services.run_pipeline import ProcessedLineItem

# A model's classification is inherently less certain than a direct name
# match, so it's given a fixed, middling confidence rather than one derived
# from anything the model reports about itself — models are not calibrated
# self-raters, and the fixed value keeps LLM-resolved rows visually distinct
# from exact/fuzzy matches in the UI.
_LLM_CONFIDENCE = 0.6


async def classify_reviews_with_llm(
    line_items: list[ProcessedLineItem],
    *,
    taxonomy: dict[str, str],
    classify: Classifier,
) -> list[ProcessedLineItem]:
    """Return a new list where any item still in REVIEW gets one LLM call
    against the client's closed taxonomy. Items that already resolved via
    exact/fuzzy matching are returned unchanged. If the taxonomy is empty,
    no calls are made at all — there's nothing for the model to choose from.
    """
    if not taxonomy:
        return line_items

    resolved: list[ProcessedLineItem] = []
    for item in line_items:
        if item.candidate.method != MappingMethod.REVIEW:
            resolved.append(item)
            continue

        result = await classify(
            ClassificationRequest(
                account_name=item.node.name,
                ancestors=item.node.ancestors,
                taxonomy=taxonomy,
            )
        )
        if result.code is None:
            resolved.append(item)
            continue

        resolved.append(
            ProcessedLineItem(
                node=item.node,
                candidate=MappingCandidate(
                    code=result.code,
                    confidence=_LLM_CONFIDENCE,
                    method=MappingMethod.LLM,
                ),
            )
        )
    return resolved
