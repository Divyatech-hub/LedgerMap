"""Optional post-processing step: send still-unresolved line items to an LLM
classifier before they're persisted to the review queue.

Kept separate from `process_workbook` (which stays synchronous, no I/O)
since this step is async, optional, and needs the client's taxonomy — none
of which the pure matching pipeline needs to know about.
"""

import asyncio
import logging

from ledgermap.domain.models import MappingCandidate, MappingMethod
from ledgermap.integrations.llm.classifier import ClassificationRequest, Classifier
from ledgermap.services.run_pipeline import ProcessedLineItem

# A model's classification is inherently less certain than a direct name
# match, so it's given a fixed, middling confidence rather than one derived
# from anything the model reports about itself — models are not calibrated
# self-raters, and the fixed value keeps LLM-resolved rows visually distinct
# from exact/fuzzy matches in the UI.
_LLM_CONFIDENCE = 0.6

# Enough parallelism to turn minutes into seconds, while staying well inside
# the model's per-minute request quota.
_MAX_CONCURRENT_CALLS = 10

logger = logging.getLogger(__name__)


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

    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_CALLS)

    async def resolve(item: ProcessedLineItem) -> ProcessedLineItem:
        if item.candidate.method != MappingMethod.REVIEW:
            return item

        request = ClassificationRequest(
            account_name=item.node.name,
            ancestors=item.node.ancestors,
            taxonomy=taxonomy,
        )
        try:
            async with semaphore:
                result = await classify(request)
        except Exception:
            # One failed call (rate limit, timeout) shouldn't sink the whole
            # upload; the line simply stays in review for the accountant.
            logger.warning(
                "LLM classification failed for %r", item.node.name, exc_info=True
            )
            return item
        if result.code is None:
            return item

        return ProcessedLineItem(
            node=item.node,
            candidate=MappingCandidate(
                code=result.code,
                confidence=_LLM_CONFIDENCE,
                method=MappingMethod.LLM,
            ),
        )

    # Calls are independent, so run them concurrently (a first-month upload
    # can send hundreds); gather() keeps the results in input order.
    return list(await asyncio.gather(*(resolve(item) for item in line_items)))
