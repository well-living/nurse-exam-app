import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, AsyncGenerator

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from sse_starlette.sse import EventSourceResponse

from db import db, create_tables


class Settings(BaseSettings):
    debug: bool = False
    allowlist_emails: str = ""  # comma-separated emails
    anthropic_api_key: str = ""
    allowed_origins: str = "http://localhost:3000"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/nurse_exam"

    model_config = {"env_prefix": "", "env_file": ".env"}

    @property
    def allowed_emails_set(self) -> set[str]:
        if not self.allowlist_emails:
            return set()
        return {e.strip() for e in self.allowlist_emails.split(",") if e.strip()}


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to database on startup
    if settings.database_url:
        await db.connect(settings.database_url)
        async with db.acquire() as conn:
            await create_tables(conn)
    yield
    # Disconnect from database on shutdown
    await db.disconnect()


app = FastAPI(title="Nurse Exam API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Models
# =============================================================================


class User(BaseModel):
    id: uuid.UUID | None = None
    email: str


class AttemptCreate(BaseModel):
    question_id: uuid.UUID
    selected_answer: int


class AttemptResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    selected_answer: int
    is_correct: bool
    correct_answer: int | None = None
    explanation: str | None = None
    created_at: datetime


class AttemptListResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    selected_answer: int
    is_correct: bool
    created_at: datetime
    question_text: str | None = None
    category: str | None = None


class CategoryStat(BaseModel):
    category: str
    total: int
    correct: int
    accuracy_rate: float


class StatsResponse(BaseModel):
    total_attempts: int
    correct_count: int
    accuracy_rate: float
    by_category: list[CategoryStat]


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] | None = None


# =============================================================================
# Dependencies
# =============================================================================


async def get_current_user(
    x_goog_authenticated_user_email: Annotated[str | None, Header()] = None,
    x_debug_email: Annotated[str | None, Header()] = None,
) -> User:
    """
    Extract user email from IAP header or debug header.
    Creates user in database if not exists.
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

    # Get or create user in database
    user_id = None
    if db.pool:
        async with db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1", email
            )
            if row:
                user_id = row["id"]
            else:
                user_id = await conn.fetchval(
                    "INSERT INTO users (email) VALUES ($1) RETURNING id", email
                )

    return User(id=user_id, email=email)


# =============================================================================
# Health Check
# =============================================================================


@app.get("/health")
async def health():
    return {"status": "ok"}


# =============================================================================
# Attempts API
# =============================================================================


@app.post("/attempts", response_model=AttemptResponse)
async def create_attempt(
    attempt: AttemptCreate,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Submit an answer and get the result."""
    if not db.pool:
        raise HTTPException(status_code=503, detail="Database not available")

    async with db.acquire() as conn:
        # Get question to check answer
        question = await conn.fetchrow(
            "SELECT correct_answer, explanation FROM questions WHERE id = $1",
            attempt.question_id,
        )
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        is_correct = attempt.selected_answer == question["correct_answer"]

        # Insert attempt
        row = await conn.fetchrow(
            """
            INSERT INTO attempts (user_id, question_id, selected_answer, is_correct)
            VALUES ($1, $2, $3, $4)
            RETURNING id, created_at
            """,
            current_user.id,
            attempt.question_id,
            attempt.selected_answer,
            is_correct,
        )

        return AttemptResponse(
            id=row["id"],
            question_id=attempt.question_id,
            selected_answer=attempt.selected_answer,
            is_correct=is_correct,
            correct_answer=question["correct_answer"],
            explanation=question["explanation"],
            created_at=row["created_at"],
        )


@app.get("/attempts", response_model=list[AttemptListResponse])
async def list_attempts(
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Get user's attempt history."""
    if not db.pool:
        raise HTTPException(status_code=503, detail="Database not available")

    async with db.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                a.id,
                a.question_id,
                a.selected_answer,
                a.is_correct,
                a.created_at,
                q.question_text,
                q.category
            FROM attempts a
            JOIN questions q ON a.question_id = q.id
            WHERE a.user_id = $1
            ORDER BY a.created_at DESC
            LIMIT $2 OFFSET $3
            """,
            current_user.id,
            limit,
            offset,
        )

        return [
            AttemptListResponse(
                id=row["id"],
                question_id=row["question_id"],
                selected_answer=row["selected_answer"],
                is_correct=row["is_correct"],
                created_at=row["created_at"],
                question_text=row["question_text"],
                category=row["category"],
            )
            for row in rows
        ]


# =============================================================================
# Stats API
# =============================================================================


@app.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get user's learning statistics."""
    if not db.pool:
        raise HTTPException(status_code=503, detail="Database not available")

    async with db.acquire() as conn:
        # Overall stats
        overall = await conn.fetchrow(
            """
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_correct) as correct
            FROM attempts
            WHERE user_id = $1
            """,
            current_user.id,
        )

        total = overall["total"] or 0
        correct = overall["correct"] or 0
        accuracy_rate = (correct / total * 100) if total > 0 else 0.0

        # Stats by category
        category_rows = await conn.fetch(
            """
            SELECT
                q.category,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE a.is_correct) as correct
            FROM attempts a
            JOIN questions q ON a.question_id = q.id
            WHERE a.user_id = $1
            GROUP BY q.category
            ORDER BY q.category
            """,
            current_user.id,
        )

        by_category = [
            CategoryStat(
                category=row["category"],
                total=row["total"],
                correct=row["correct"],
                accuracy_rate=(row["correct"] / row["total"] * 100)
                if row["total"] > 0
                else 0.0,
            )
            for row in category_rows
        ]

        return StatsResponse(
            total_attempts=total,
            correct_count=correct,
            accuracy_rate=accuracy_rate,
            by_category=by_category,
        )


# =============================================================================
# Chat API
# =============================================================================


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
