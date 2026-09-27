"""Gemini-backed implementation of `ChatCorrectionInterpreter`.

Mirrors the Anthropic version: a forced function call (mode ANY, restricted
to our one function) guarantees a structured response, and the shared
`result_from_payload` then checks the ids and code against what exists.
"""

from ledgermap.config import get_settings
from ledgermap.integrations.llm.anthropic_chat_correction import (
    _SYSTEM_PROMPT,
    _TOOL_NAME,
    _TOOL_SCHEMA,
    _build_user_message,
)
from ledgermap.integrations.llm.chat_correction import (
    ChatCorrectionRequest,
    ChatCorrectionResult,
    result_from_payload,
)
from ledgermap.integrations.llm.gemini_client import get_gemini_client


async def interpret_chat_correction_with_gemini(
    request: ChatCorrectionRequest,
) -> ChatCorrectionResult:
    from google.genai import types

    function = types.FunctionDeclaration(
        name=_TOOL_NAME,
        description=_TOOL_SCHEMA["description"],
        parameters_json_schema=_TOOL_SCHEMA["input_schema"],
    )
    response = await get_gemini_client().aio.models.generate_content(
        model=get_settings().gemini_model,
        contents=_build_user_message(request),
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            temperature=0,
            max_output_tokens=512,
            tools=[types.Tool(function_declarations=[function])],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode=types.FunctionCallingConfigMode.ANY,
                    allowed_function_names=[_TOOL_NAME],
                )
            ),
        ),
    )

    call = next(iter(response.function_calls or []), None)
    if call is None or call.args is None:
        return ChatCorrectionResult(
            line_item_id=None,
            resulting_code=None,
            candidate_ids=(),
            explanation="The model didn't return a usable response.",
        )

    return result_from_payload(dict(call.args), request)
