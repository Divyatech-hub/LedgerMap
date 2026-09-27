"""Pick the configured LLM provider's implementations.

The only place that knows which providers exist; callers get back a plain
`Classifier` / `ChatCorrectionInterpreter` and never import a provider module
themselves. Imports are lazy so only the selected provider's SDK needs to be
installed.
"""

from ledgermap.config import get_settings
from ledgermap.integrations.llm.chat_correction import ChatCorrectionInterpreter
from ledgermap.integrations.llm.classifier import Classifier


def get_classifier() -> Classifier:
    if get_settings().llm_provider == "anthropic":
        from ledgermap.integrations.llm import anthropic_classifier

        return anthropic_classifier.classify_with_anthropic

    from ledgermap.integrations.llm import gemini_classifier

    return gemini_classifier.classify_with_gemini


def get_chat_interpreter() -> ChatCorrectionInterpreter:
    if get_settings().llm_provider == "anthropic":
        from ledgermap.integrations.llm import anthropic_chat_correction

        return anthropic_chat_correction.interpret_chat_correction_with_anthropic

    from ledgermap.integrations.llm import gemini_chat_correction

    return gemini_chat_correction.interpret_chat_correction_with_gemini
