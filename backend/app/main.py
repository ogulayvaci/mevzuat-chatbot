import logging
import httpx

from app.config import MCP_SERVER_URL
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from app.services.openai_service import get_chat_response, stream_chat_response

logger = logging.getLogger(__name__)

app = FastAPI(title="Mevzuat Chatbot API")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


async def safe_stream(message: str):
    try:
        async for chunk in stream_chat_response(message):
            yield chunk
    except Exception:
        logger.exception("Streaming chat failed")

        yield (
            "\n\nYanıt oluşturulurken bir hata oluştu. "
            "Lütfen tekrar deneyin."
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    try:
        mcp_health_url = MCP_SERVER_URL.replace("/mcp", "/health")

        async with httpx.AsyncClient(timeout=5) as http_client:
            response = await http_client.get(mcp_health_url)
            response.raise_for_status()

        return {
            "status": "healthy",
            "mcp": "online",
        }

    except Exception:
        return {
            "status": "degraded",
            "mcp": "offline",
        }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        message = request.message.strip()

        if not message:
            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty.",
            )

        answer = await get_chat_response(message)

        if not answer.strip():
            raise HTTPException(
                status_code=502,
                detail="The model returned an empty response.",
            )

        return {"answer": answer}

    except HTTPException:
        raise

    except Exception:
        logger.exception("Chat request failed")

        raise HTTPException(
            status_code=500,
            detail="Yanıt oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.",
        )


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    return StreamingResponse(
        safe_stream(message),
        media_type="text/plain",
    )