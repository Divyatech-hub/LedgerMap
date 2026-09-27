"""Gemini-backed implementation of `ChatCorrectionInterpreter`.

A forced function call (mode ANY, restricted to our one function) guarantees
a structured response rather than free text to parse. The function is never
executed; `result_from_payload` then checks the returned ids and code against
what actually exists.
"""

from ledgermap.config import get_settings
from ledgermap.integrations.llm.chat_correction import (
    SYSTEM_PROMPT,
    TOOL_NAME,
    TOOL_SCHEMA,
    ChatCorrectionRequest,
    ChatCorrectionResult,
    build_user_message,
    result_from_payload,
)
from ledgermap.integrations.llm.gemini_client import get_gemini_client


async def interpret_chat_correction_with_gemini(
    request: ChatCorrectionRequest,
) -> ChatCorrectionResult:
    from google.genai import types

    function = types.FunctionDeclaration(
        name=TOOL_NAME,
        description=TOOL_SCHEMA["description"],
        parameters_json_schema=TOOL_SCHEMA["parameters"],
    )
    response = await get_gemini_client().aio.models.generate_content(
        model=get_settings().gemini_model,
        contents=build_user_message(request),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            max_output_tokens=512,
            # We read the structured answer ourselves; the SDK shouldn't try
            # to execute anything on our behalf.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
            tools=[types.Tool(function_declarations=[function])],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode=types.FunctionCallingConfigMode.ANY,
                    allowed_function_names=[TOOL_NAME],
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
