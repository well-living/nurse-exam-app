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
