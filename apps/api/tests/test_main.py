import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest


class TestHealth:
    async def test_health_returns_ok(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAuthentication:
    async def test_chat_requires_auth(self, client):
        """Chat endpoint should return 401 without auth headers."""
        response = await client.post(
            "/chat/stream",
            json={"message": "test"},
        )
        assert response.status_code == 401

    async def test_debug_email_header_works_in_debug_mode(
        self, client, enable_debug
    ):
        """X-Debug-Email should work when debug=True."""
        response = await client.post(
            "/chat/stream",
            json={"message": "test"},
            headers={"X-Debug-Email": "test@example.com"},
        )
        assert response.status_code == 200

    async def test_debug_email_header_ignored_in_production(self, client):
        """X-Debug-Email should be ignored when debug=False."""
        response = await client.post(
            "/chat/stream",
            json={"message": "test"},
            headers={"X-Debug-Email": "test@example.com"},
        )
        assert response.status_code == 401

    async def test_iap_header_works(self, client, enable_debug):
        """X-Goog-Authenticated-User-Email should work."""
        response = await client.post(
            "/chat/stream",
            json={"message": "test"},
            headers={
                "X-Goog-Authenticated-User-Email": "accounts.google.com:user@example.com"
            },
        )
        assert response.status_code == 200

    async def test_allowlist_blocks_unauthorized_email(self, client, set_allowlist):
        """Non-allowlisted email should be blocked in production."""
        response = await client.post(
            "/chat/stream",
            json={"message": "test"},
            headers={
                "X-Goog-Authenticated-User-Email": "accounts.google.com:notallowed@example.com"
            },
        )
        assert response.status_code == 403

    async def test_allowlist_allows_authorized_email(self, client, set_allowlist):
        """Allowlisted email should be allowed in production."""
        response = await client.post(
            "/chat/stream",
            json={"message": "test"},
            headers={
                "X-Goog-Authenticated-User-Email": "accounts.google.com:allowed@example.com"
            },
        )
        assert response.status_code == 200


class TestChatStream:
    async def test_chat_stream_returns_sse(self, client, enable_debug):
        """Chat endpoint should return SSE content type."""
        response = await client.post(
            "/chat/stream",
            json={"message": "こんにちは"},
            headers={"X-Debug-Email": "test@example.com"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    async def test_chat_stream_with_history(self, client, enable_debug):
        """Chat endpoint should accept history."""
        response = await client.post(
            "/chat/stream",
            json={
                "message": "続けて",
                "history": [
                    {"role": "user", "content": "看護について教えて"},
                    {"role": "assistant", "content": "看護とは..."},
                ],
            },
            headers={"X-Debug-Email": "test@example.com"},
        )
        assert response.status_code == 200


class TestAttempts:
    async def test_attempts_requires_auth(self, client):
        """Attempts endpoint should return 401 without auth."""
        response = await client.get("/attempts")
        assert response.status_code == 401

    async def test_create_attempt_requires_db(self, client, enable_debug):
        """Create attempt should return 503 when DB is not available."""
        response = await client.post(
            "/attempts",
            json={
                "question_id": str(uuid.uuid4()),
                "selected_answer": 1,
            },
            headers={"X-Debug-Email": "test@example.com"},
        )
        assert response.status_code == 503

    async def test_list_attempts_requires_db(self, client, enable_debug):
        """List attempts should return 503 when DB is not available."""
        response = await client.get(
            "/attempts",
            headers={"X-Debug-Email": "test@example.com"},
        )
        assert response.status_code == 503

    async def test_create_attempt_with_mock_db(
        self, client, enable_debug, mock_db, sample_user_id, sample_question_id
    ):
        """Create attempt should work with mocked DB."""
        attempt_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        # Mock user lookup
        mock_db.fetchrow.side_effect = [
            {"id": sample_user_id},  # User lookup
            {"correct_answer": 1, "explanation": "Test explanation"},  # Question lookup
        ]
        mock_db.fetchval.return_value = sample_user_id

        # Mock attempt insert - create a separate mock for this call
        async def mock_fetchrow_sequence(*args, **kwargs):
            # Check which query is being made
            query = args[0] if args else ""
            if "SELECT id FROM users" in query:
                return {"id": sample_user_id}
            elif "SELECT correct_answer" in query:
                return {"correct_answer": 1, "explanation": "Test explanation"}
            elif "INSERT INTO attempts" in query:
                return {"id": attempt_id, "created_at": now}
            return None

        mock_db.fetchrow = AsyncMock(side_effect=mock_fetchrow_sequence)

        response = await client.post(
            "/attempts",
            json={
                "question_id": str(sample_question_id),
                "selected_answer": 1,
            },
            headers={"X-Debug-Email": "test@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_correct"] is True
        assert data["correct_answer"] == 1

    async def test_list_attempts_with_mock_db(
        self, client, enable_debug, mock_db, sample_user_id, sample_question_id
    ):
        """List attempts should work with mocked DB."""
        attempt_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        async def mock_fetchrow_sequence(*args, **kwargs):
            query = args[0] if args else ""
            if "SELECT id FROM users" in query:
                return {"id": sample_user_id}
            return None

        mock_db.fetchrow = AsyncMock(side_effect=mock_fetchrow_sequence)
        mock_db.fetch = AsyncMock(
            return_value=[
                {
                    "id": attempt_id,
                    "question_id": sample_question_id,
                    "selected_answer": 1,
                    "is_correct": True,
                    "created_at": now,
                    "question_text": "Test question",
                    "category": "基礎看護学",
                }
            ]
        )

        response = await client.get(
            "/attempts",
            headers={"X-Debug-Email": "test@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_correct"] is True


class TestStats:
    async def test_stats_requires_auth(self, client):
        """Stats endpoint should return 401 without auth."""
        response = await client.get("/stats")
        assert response.status_code == 401

    async def test_stats_requires_db(self, client, enable_debug):
        """Stats should return 503 when DB is not available."""
        response = await client.get(
            "/stats",
            headers={"X-Debug-Email": "test@example.com"},
        )
        assert response.status_code == 503

    async def test_stats_with_mock_db(
        self, client, enable_debug, mock_db, sample_user_id
    ):
        """Stats should return correct data with mocked DB."""

        async def mock_fetchrow_sequence(*args, **kwargs):
            query = args[0] if args else ""
            if "SELECT id FROM users" in query:
                return {"id": sample_user_id}
            elif "COUNT(*)" in query and "FILTER" in query:
                return {"total": 10, "correct": 7}
            return None

        mock_db.fetchrow = AsyncMock(side_effect=mock_fetchrow_sequence)
        mock_db.fetch = AsyncMock(
            return_value=[
                {"category": "基礎看護学", "total": 5, "correct": 4},
                {"category": "成人看護学", "total": 5, "correct": 3},
            ]
        )

        response = await client.get(
            "/stats",
            headers={"X-Debug-Email": "test@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_attempts"] == 10
        assert data["correct_count"] == 7
        assert data["accuracy_rate"] == 70.0
        assert len(data["by_category"]) == 2

    async def test_stats_empty_with_mock_db(
        self, client, enable_debug, mock_db, sample_user_id
    ):
        """Stats should handle zero attempts."""

        async def mock_fetchrow_sequence(*args, **kwargs):
            query = args[0] if args else ""
            if "SELECT id FROM users" in query:
                return {"id": sample_user_id}
            elif "COUNT(*)" in query:
                return {"total": 0, "correct": 0}
            return None

        mock_db.fetchrow = AsyncMock(side_effect=mock_fetchrow_sequence)
        mock_db.fetch = AsyncMock(return_value=[])

        response = await client.get(
            "/stats",
            headers={"X-Debug-Email": "test@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_attempts"] == 0
        assert data["correct_count"] == 0
        assert data["accuracy_rate"] == 0.0
        assert data["by_category"] == []
