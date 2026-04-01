"""
Tests for session state correctness under concurrent or rapid successive queries.

These tests cover the server-side risk exposed by the frontend bug where
suggested question buttons were not disabled during generation, allowing users
to fire multiple requests to the same session in rapid succession.

All sub-components are mocked — no ChromaDB or Anthropic API calls.

Covers:
- Cancel flag is cleared at the start of each new query (stale cancel guard)
- A cancelled query does not corrupt session history
- A second query after a cancel proceeds correctly with a clean cancel flag
- Cancel state correctly prevents history updates when generation is interrupted
"""
import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Fixture: RAGSystem with all sub-components mocked (same pattern as test_rag_system.py)
# ---------------------------------------------------------------------------

@pytest.fixture
def rag():
    """
    Build a RAGSystem with all sub-components replaced by MagicMocks.
    Follows the same fixture pattern as test_rag_system.py.
    """
    with patch("rag_system.VectorStore") as MockVS, \
         patch("rag_system.AIGenerator") as MockAI, \
         patch("rag_system.DocumentProcessor") as MockDP, \
         patch("rag_system.SessionManager") as MockSM:

        config = MagicMock()
        config.ANTHROPIC_API_KEY = "fake_key"
        config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
        config.CHROMA_PATH = "/tmp/test_chroma"
        config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        config.MAX_RESULTS = 5
        config.MAX_HISTORY = 2
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100

        from rag_system import RAGSystem
        system = RAGSystem(config)

        system._mock_ai = MockAI.return_value
        system._mock_vs = MockVS.return_value
        system._mock_sm = MockSM.return_value

        system._mock_ai.generate_response.return_value = "Default answer"
        system._mock_sm.get_conversation_history.return_value = None
        system._mock_sm.is_cancelled.return_value = False

        system.tool_manager = MagicMock()
        system.tool_manager.get_tool_definitions.return_value = [{"name": "search_course_content"}]
        system.tool_manager.get_last_sources.return_value = []

        yield system


# ---------------------------------------------------------------------------
# Cancel flag lifecycle
# ---------------------------------------------------------------------------

class TestCancelFlagLifecycle:

    def test_cancel_flag_is_cleared_at_the_start_of_every_query(self, rag):
        """
        RAGSystem.query() must call clear_cancel() before generating a response.
        This ensures a stale cancel flag from a previous interrupted request
        does not suppress the result of a new legitimate request to the same session.
        """
        rag.query("what is RAG?", session_id="session_1")

        rag._mock_sm.clear_cancel.assert_called_with("session_1")

    def test_cancel_flag_cleared_before_generation_starts(self, rag):
        """
        clear_cancel() must be called before generate_response(), not after.
        If the order were reversed, a concurrent cancel during generation
        would be wiped out before it had any effect.
        """
        call_order = []
        rag._mock_sm.clear_cancel.side_effect = lambda sid: call_order.append("clear_cancel")
        rag._mock_ai.generate_response.side_effect = lambda **kw: call_order.append("generate") or "answer"

        rag.query("test question", session_id="session_1")

        assert call_order == ["clear_cancel", "generate"]

    def test_no_clear_cancel_called_without_session_id(self, rag):
        """
        clear_cancel() should only be called when a session_id is provided.
        Stateless queries (no session) must not touch the cancel registry.
        """
        rag.query("standalone question")

        rag._mock_sm.clear_cancel.assert_not_called()


# ---------------------------------------------------------------------------
# Cancelled query behaviour
# ---------------------------------------------------------------------------

class TestCancelledQueryBehaviour:

    def test_cancelled_query_returns_interrupted_message(self, rag):
        """
        If the session is marked cancelled by the time generate_response() returns
        (i.e., the user clicked Pause mid-generation), the system must discard
        the AI's response and return the interruption message instead.
        """
        rag._mock_sm.is_cancelled.return_value = True
        rag._mock_ai.generate_response.return_value = "A full but unwanted answer"

        response, sources = rag.query("some question", session_id="session_1")

        assert response == "Generation was interrupted."
        assert sources == []

    def test_cancelled_query_does_not_update_session_history(self, rag):
        """
        A cancelled query must NOT add to conversation history.
        If it did, the interrupted exchange would pollute future context,
        causing the assistant to reference an answer the user never received.
        """
        rag._mock_sm.is_cancelled.return_value = True

        rag.query("interrupted question", session_id="session_1")

        rag._mock_sm.add_exchange.assert_not_called()

    def test_cancelled_query_clears_its_own_cancel_flag(self, rag):
        """
        After handling a cancellation, the cancel flag must be cleared so the
        next query to the same session is not falsely treated as cancelled.
        """
        rag._mock_sm.is_cancelled.return_value = True

        rag.query("interrupted question", session_id="session_1")

        # clear_cancel is called twice: once at query start, once after cancel detected
        assert rag._mock_sm.clear_cancel.call_count == 2
        rag._mock_sm.clear_cancel.assert_called_with("session_1")


# ---------------------------------------------------------------------------
# Second request after cancellation
# ---------------------------------------------------------------------------

class TestSecondRequestAfterCancellation:

    def test_second_query_clears_stale_cancel_flag_from_first(self, rag):
        """
        Simulates two rapid successive queries to the same session (the frontend bug).
        The second query must call clear_cancel() so the cancel flag set during
        the first query's generation does not bleed into the second query's result.
        """
        # First query: user cancels mid-generation
        rag._mock_sm.is_cancelled.return_value = True
        rag.query("first question", session_id="session_1")

        # Second query arrives (simulating a suggested question click that wasn't blocked)
        rag._mock_sm.is_cancelled.return_value = False
        rag._mock_ai.generate_response.return_value = "Second answer"
        response, _ = rag.query("second question", session_id="session_1")

        assert response == "Second answer"

    def test_second_query_updates_history_independently_of_first(self, rag):
        """
        Even if the first query was cancelled and did not update history,
        the second query (not cancelled) must update history with its own exchange.
        """
        # First query: cancelled — no history update
        rag._mock_sm.is_cancelled.return_value = True
        rag.query("first question", session_id="session_1")
        rag._mock_sm.add_exchange.assert_not_called()

        # Second query: completes normally — must update history
        rag._mock_sm.is_cancelled.return_value = False
        rag._mock_ai.generate_response.return_value = "Second answer"
        rag.query("second question", session_id="session_1")

        rag._mock_sm.add_exchange.assert_called_once_with("session_1", "second question", "Second answer")
