"""
Tests for FastAPI endpoints in app.py.

All sub-components are mocked via the api_client / api_mock_rag fixtures in
conftest.py, so tests run without ChromaDB, the Anthropic API, or a live
frontend directory.

Covers:
- POST /api/query   — request validation, session handling, response schema, error path
- GET  /api/courses — analytics response, error path
- DELETE /api/session/{session_id} — 204 + delegation to SessionManager
- POST  /api/cancel/{session_id}   — 204 + delegation to SessionManager
"""


class TestQueryEndpoint:

    def test_returns_200_on_valid_request(self, api_client):
        response = api_client.post("/api/query", json={"query": "What is RAG?"})
        assert response.status_code == 200

    def test_response_schema_contains_answer_sources_session_id(self, api_client, api_mock_rag):
        api_mock_rag.query.return_value = ("RAG uses retrieval to ground answers.", ["Source 1"])
        api_mock_rag.session_manager.create_session.return_value = "new-session"

        body = api_client.post("/api/query", json={"query": "What is RAG?"}).json()

        assert body["answer"] == "RAG uses retrieval to ground answers."
        assert body["sources"] == ["Source 1"]
        assert body["session_id"] == "new-session"

    def test_creates_session_when_none_provided(self, api_client, api_mock_rag):
        api_mock_rag.session_manager.create_session.return_value = "auto-session"

        body = api_client.post("/api/query", json={"query": "test"}).json()

        api_mock_rag.session_manager.create_session.assert_called_once()
        assert body["session_id"] == "auto-session"

    def test_uses_provided_session_id(self, api_client, api_mock_rag):
        body = api_client.post(
            "/api/query", json={"query": "follow-up", "session_id": "existing-session"}
        ).json()

        api_mock_rag.session_manager.create_session.assert_not_called()
        assert body["session_id"] == "existing-session"

    def test_passes_query_and_session_id_to_rag(self, api_client, api_mock_rag):
        api_client.post(
            "/api/query", json={"query": "test question", "session_id": "sess-123"}
        )

        api_mock_rag.query.assert_called_once_with("test question", "sess-123")

    def test_returns_500_when_rag_raises(self, api_client, api_mock_rag):
        api_mock_rag.query.side_effect = Exception("Vector DB connection failed")

        response = api_client.post("/api/query", json={"query": "test"})

        assert response.status_code == 500
        assert "Vector DB connection failed" in response.json()["detail"]

    def test_missing_query_field_returns_422(self, api_client):
        response = api_client.post("/api/query", json={})
        assert response.status_code == 422

    def test_empty_sources_list_is_valid(self, api_client, api_mock_rag):
        api_mock_rag.query.return_value = ("Direct answer.", [])

        body = api_client.post("/api/query", json={"query": "general knowledge"}).json()

        assert body["sources"] == []


class TestCoursesEndpoint:

    def test_returns_200(self, api_client):
        response = api_client.get("/api/courses")
        assert response.status_code == 200

    def test_returns_total_courses_and_titles(self, api_client, api_mock_rag):
        api_mock_rag.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["Course A", "Course B", "Course C"],
        }

        body = api_client.get("/api/courses").json()

        assert body["total_courses"] == 3
        assert body["course_titles"] == ["Course A", "Course B", "Course C"]

    def test_empty_catalog_returns_zero_courses(self, api_client, api_mock_rag):
        api_mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        body = api_client.get("/api/courses").json()

        assert body["total_courses"] == 0
        assert body["course_titles"] == []

    def test_returns_500_when_analytics_raises(self, api_client, api_mock_rag):
        api_mock_rag.get_course_analytics.side_effect = Exception("DB unavailable")

        response = api_client.get("/api/courses")

        assert response.status_code == 500
        assert "DB unavailable" in response.json()["detail"]


class TestDeleteSessionEndpoint:

    def test_returns_204(self, api_client):
        response = api_client.delete("/api/session/some-session-id")
        assert response.status_code == 204

    def test_delegates_to_session_manager(self, api_client, api_mock_rag):
        api_client.delete("/api/session/sess-abc")

        api_mock_rag.session_manager.delete_session.assert_called_once_with("sess-abc")

    def test_delete_nonexistent_session_returns_204(self, api_client):
        """delete_session is fire-and-forget; no error is raised for unknown IDs."""
        response = api_client.delete("/api/session/does-not-exist")
        assert response.status_code == 204


class TestCancelEndpoint:

    def test_returns_204(self, api_client):
        response = api_client.post("/api/cancel/some-session-id")
        assert response.status_code == 204

    def test_delegates_to_session_manager(self, api_client, api_mock_rag):
        api_client.post("/api/cancel/sess-xyz")

        api_mock_rag.session_manager.cancel.assert_called_once_with("sess-xyz")
