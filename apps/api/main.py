import asyncio
from contextlib import asynccontextmanager
from typing import Annotated, AsyncGenerator

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from sse_starlette.sse import EventSourceResponse


class Settings(BaseSettings):
    debug: bool = False
    allowlist_emails: str = ""  # comma-separated emails
    anthropic_api_key: str = ""
    allowed_origins: str = "http://localhost:3000"

    model_config = {"env_prefix": "", "env_file": ".env"}

    @property
    def allowed_emails_set(self) -> set[str]:
        if not self.allowlist_emails:
            return set()
        return {e.strip() for e in self.allowlist_emails.split(",") if e.strip()}


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Nurse Exam API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class User(BaseModel):
    email: str


def get_current_user(
    x_goog_authenticated_user_email: Annotated[str | None, Header()] = None,
    x_debug_email: Annotated[str | None, Header()] = None,
) -> User:
    """
    Extract user email from IAP header or debug header.

    In production (GCP IAP):
      - Uses X-Goog-Authenticated-User-Email header (format: "accounts.google.com:email@example.com")

    In local development (debug=True):
      - Allows X-Debug-Email header
    """
    email: str | None = None

    # IAP header format: "accounts.google.com:email@example.com"
    if x_goog_authenticated_user_email:
        parts = x_goog_authenticated_user_email.split(":")
        email = parts[1] if len(parts) > 1 else parts[0]

    # Allow debug header in debug mode
    if settings.debug and x_debug_email:
        email = x_debug_email

    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Check allowlist in production
    if not settings.debug and settings.allowed_emails_set:
        if email not in settings.allowed_emails_set:
            raise HTTPException(status_code=403, detail="Access denied")

    return User(email=email)


@app.get("/health")
async def health():
    return {"status": "ok"}


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] | None = None


async def generate_chat_response(
    message: str,
    history: list[dict[str, str]] | None = None,
) -> AsyncGenerator[str, None]:
    """
    Generate chat response using Anthropic API with streaming.
    Falls back to mock response if API key is not set.
    """
    if not settings.anthropic_api_key:
        # Mock response for development without API key
        mock_response = f"[Mock Response] あなたの質問: {message}\n\nこれはAPIキーが設定されていない場合のモック応答です。"
        for char in mock_response:
            yield char
            await asyncio.sleep(0.02)
        return

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        messages = []
        if history:
            for h in history:
                messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        system_prompt = """あなたは看護師国家試験の学習をサポートするAIアシスタントです。
医学・看護学に関する質問に丁寧に回答してください。

重要な免責事項:
- このチャットは学習支援を目的としており、医療上のアドバイスではありません
- 実際の医療判断は必ず医療専門家にご相談ください
- 試験対策としての知識提供を目的としています"""

        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text

    except Exception as e:
        yield f"[Error] チャットの処理中にエラーが発生しました: {str(e)}"


@app.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    SSE endpoint for chat streaming.
    Requires authentication via IAP or debug header.
    """

    async def event_generator():
        async for chunk in generate_chat_response(
            request.message,
            request.history,
        ):
            yield {"event": "message", "data": chunk}
        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
