import json

from openai import AsyncOpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.services.mcp_service import call_mcp_tool


client = AsyncOpenAI(api_key=OPENAI_API_KEY)

MAX_TOOL_ROUNDS = 6


SYSTEM_PROMPT = """
You are an assistant specialized in Turkish legislation.

Use the available tools whenever legislation information is needed.
Do not invent legislation, article numbers, or legal provisions.

When answering a question about the content of a specific legislation:
1. First use search_mevzuat with the legislation number or title to obtain mevzuatId.
2. Then use search_within_mevzuat with that mevzuatId to find the relevant provision.
3. Do not repeatedly call search_mevzuat to search inside the same legislation.

If information cannot be verified using the tools, clearly say so.

Answer in the language used by the user.
"""


TOOLS = [
    {
        "type": "function",
        "name": "search_mevzuat",
        "description": (
            "Find Turkish legislation and obtain its mevzuatId. "
            "Use this tool first when a user refers to a law or legislation. "
            "Search by official legislation number or title. "
            "Do NOT use this tool to search for words inside a known legislation. "
            "After obtaining mevzuatId, use search_within_mevzuat for that."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "mevzuat_adi": {
                    "type": "string",
                    "description": "Legislation title or title keywords.",
                },
                "mevzuat_no": {
                    "type": "string",
                    "description": "Official legislation number, for example 6698.",
                },
                "page_size": {
                    "type": "integer",
                    "description": "Maximum number of search results. Use 20 or less.",
                    "default": 20,
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_mevzuat_content",
        "description": (
            "Get the full content of a legislation document using its mevzuatId."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "mevzuat_id": {
                    "type": "string",
                    "description": "The mevzuatId returned by search_mevzuat.",
                }
            },
            "required": ["mevzuat_id"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "search_within_mevzuat",
        "description": (
            "Search for a keyword or phrase inside a specific legislation document. "
            "Use this after search_mevzuat has returned a mevzuatId. "
            "For questions about a concept, article, rule, definition, obligation, "
            "exception, or phrase inside a known law, prefer this tool."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "mevzuat_id": {
                    "type": "string",
                    "description": "The mevzuatId returned by search_mevzuat.",
                },
                "keyword": {
                    "type": "string",
                    "description": "Keyword or phrase to search inside the legislation.",
                },
                "case_sensitive": {
                    "type": "boolean",
                    "default": False,
                },
                "max_results": {
                    "type": "integer",
                    "default": 25,
                },
            },
            "required": ["mevzuat_id", "keyword"],
            "additionalProperties": False,
        },
    },
]


async def execute_tool_calls(response):
    tool_outputs = []

    for tool_call in response.output:
        if tool_call.type != "function_call":
            continue

        arguments = json.loads(tool_call.arguments)

        if tool_call.name == "search_mevzuat":
            arguments.setdefault("page_size", 20)
            arguments["page_size"] = min(arguments["page_size"], 20)

        result = await call_mcp_tool(
            tool_call.name,
            arguments,
        )

        tool_outputs.append(
            {
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": str(result),
            }
        )

    return tool_outputs


async def get_chat_response(message: str) -> str:
    response = await client.responses.create(
        model=OPENAI_MODEL,
        instructions=SYSTEM_PROMPT,
        input=message,
        tools=TOOLS,
    )

    tool_rounds = 0

    while True:
        tool_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        if not tool_calls:
            answer = response.output_text.strip()

            if not answer:
                return (
                    "Bu soru için doğrulanmış bir yanıt oluşturamadım. "
                    "Lütfen sorunuzu biraz daha açık şekilde yeniden sorun."
                )

            return answer

        if tool_rounds >= MAX_TOOL_ROUNDS:
            return (
                "İlgili mevzuat bilgisine ulaşmak için çok fazla araç çağrısı gerekti. "
                "Lütfen sorunuzu biraz daha spesifik şekilde yeniden sorun."
            )

        tool_outputs = await execute_tool_calls(response)
        tool_rounds += 1

        response = await client.responses.create(
            model=OPENAI_MODEL,
            instructions=SYSTEM_PROMPT,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=TOOLS,
        )


async def stream_chat_response(message: str):
    response = await client.responses.create(
        model=OPENAI_MODEL,
        instructions=SYSTEM_PROMPT,
        input=message,
        tools=TOOLS,
    )

    for _ in range(MAX_TOOL_ROUNDS):
        tool_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        if not tool_calls:
            # İlk response zaten final text ürettiyse:
            if response.output_text.strip():
                yield response.output_text
                return

            yield (
                "Bu soru için doğrulanmış bir yanıt oluşturamadım. "
                "Lütfen sorunuzu biraz daha açık şekilde yeniden sorun."
            )
            return

        tool_outputs = await execute_tool_calls(response)

        # Tool sonucundan sonraki cevabı gerçek stream olarak alıyoruz.
        stream = await client.responses.create(
            model=OPENAI_MODEL,
            instructions=SYSTEM_PROMPT,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=TOOLS,
            stream=True,
        )

        streamed_text = []
        next_response = None

        async for event in stream:
            if event.type == "response.output_text.delta":
                delta = event.delta

                if delta:
                    streamed_text.append(delta)
                    yield delta

            elif event.type == "response.completed":
                next_response = event.response

        if next_response is None:
            yield "\nYanıt oluşturulurken bir hata oluştu."
            return

        next_tool_calls = [
            item
            for item in next_response.output
            if item.type == "function_call"
        ]

        if not next_tool_calls:
            if streamed_text:
                return

            yield (
                "Bu soru için doğrulanmış bir yanıt oluşturamadım. "
                "Lütfen sorunuzu biraz daha açık şekilde yeniden sorun."
            )
            return

        # Model başka bir MCP tool çağırmak istiyorsa
        # yeni response ile loop'a devam ediyoruz.
        response = next_response

    yield (
        "İlgili mevzuat bilgisine ulaşmak için çok fazla araç çağrısı gerekti. "
        "Lütfen sorunuzu biraz daha spesifik şekilde yeniden sorun."
    )