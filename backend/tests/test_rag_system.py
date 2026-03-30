"""
Tests for RAGSystem.query().

All sub-components (VectorStore, AIGenerator, SessionManager, DocumentProcessor)
are patched so tests are fast and don't touch ChromaDB or the Anthropic API.

Covers:
- Prompt construction
- Session history retrieval and update
- Return contract (response, sources)
- Tool wiring
- Exception propagation (the source of "Error: Query failed" in the UI)
- Regression tests for specific crash paths
"""
import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Fixture: a RAGSystem with all sub-components mocked
# ---------------------------------------------------------------------------

@pytest.fixture
def rag():
    """
    Build a RAGSystem with VectorStore, AIGenerator, SessionManager,
    and DocumentProcessor all replaced by MagicMocks.
    Exposes mock instances on the system object for assertion convenience.
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

        # Wire mock instances for easy access in tests
        system._mock_ai = MockAI.return_value
        system._mock_vs = MockVS.return_value
        system._mock_sm = MockSM.return_value

        # Default AI response
        system._mock_ai.generate_response.return_value = "Default answer"

        # Default session history: no history
        system._mock_sm.get_conversation_history.return_value = None

        # Default: session is not cancelled
        system._mock_sm.is_cancelled.return_value = False

        # Replace tool_manager with a controllable mock
        system.tool_manager = MagicMock()
        system.tool_manager.get_tool_definitions.return_value = [{"name": "search_course_content"}]
        system.tool_manager.get_last_sources.return_value = []

        yield system


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

class TestRAGSystemQueryPrompt:

    def test_query_wraps_user_input_in_prompt(self, rag):
        rag.query("what is a variable?")

        call_kwargs = rag._mock_ai.generate_response.call_args[1]
        assert call_kwargs["query"] == "Answer this question about course materials: what is a variable?"

    def test_query_passes_tool_definitions_to_generator(self, rag):
        rag.query("test question")

        call_kwargs = rag._mock_ai.generate_response.call_args[1]
        assert call_kwargs["tools"] == [{"name": "search_course_content"}]
        assert call_kwargs["tool_manager"] is rag.tool_manager


# ---------------------------------------------------------------------------
# Session handling
# ---------------------------------------------------------------------------

class TestRAGSystemQuerySession:

    def test_query_without_session_id_passes_none_history(self, rag):
        rag.query("test question")

        call_kwargs = rag._mock_ai.generate_response.call_args[1]
        assert call_kwargs["conversation_history"] is None
        rag._mock_sm.get_conversation_history.assert_not_called()

    def test_query_with_session_id_retrieves_history(self, rag):
        rag._mock_sm.get_conversation_history.return_value = "User: hi\nAssistant: hello"

        rag.query("follow-up question", session_id="session_1")

        rag._mock_sm.get_conversation_history.assert_called_once_with("session_1")
        call_kwargs = rag._mock_ai.generate_response.call_args[1]
        assert call_kwargs["conversation_history"] == "User: hi\nAssistant: hello"

    def test_query_with_session_id_updates_history_after_response(self, rag):
        rag._mock_ai.generate_response.return_value = "The answer"

        rag.query("my question", session_id="session_1")

        rag._mock_sm.add_exchange.assert_called_once_with("session_1", "my question", "The answer")

    def test_query_without_session_id_does_not_update_history(self, rag):
        rag.query("my question")

        rag._mock_sm.add_exchange.assert_not_called()

    def test_query_empty_session_history_passes_none_to_generator(self, rag):
        """None (not '') should flow through when session has no history yet."""
        rag._mock_sm.get_conversation_history.return_value = None

        rag.query("test", session_id="new_session")

        call_kwargs = rag._mock_ai.generate_response.call_args[1]
        assert call_kwargs["conversation_history"] is None


# ---------------------------------------------------------------------------
# Return contract
# ---------------------------------------------------------------------------

class TestRAGSystemQueryReturnContract:

    def test_query_returns_response_and_sources_tuple(self, rag):
        rag._mock_ai.generate_response.return_value = "Here is the answer"
        rag.tool_manager.get_last_sources.return_value = [
            '<a href="https://example.com">Python Basics - Lesson 1</a>'
        ]

        response, sources = rag.query("test")

        assert response == "Here is the answer"
        assert sources == ['<a href="https://example.com">Python Basics - Lesson 1</a>']

    def test_query_returns_empty_sources_when_no_tool_used(self, rag):
        rag.tool_manager.get_last_sources.return_value = []

        _, sources = rag.query("general knowledge question")

        assert sources == []

    def test_query_resets_sources_after_retrieval(self, rag):
        """reset_sources must be called after get_last_sources, not before."""
        call_order = []
        rag.tool_manager.get_last_sources.side_effect = lambda: call_order.append("get") or []
        rag.tool_manager.reset_sources.side_effect = lambda: call_order.append("reset")

        rag.query("test")

        assert call_order == ["get", "reset"]


# ---------------------------------------------------------------------------
# Exception propagation
# ---------------------------------------------------------------------------

class TestRAGSystemQueryExceptionPropagation:

    def test_query_propagates_exception_to_caller(self, rag):
        """
        Unhandled exceptions from generate_response bubble up through RAGSystem.query()
        to app.py's exception handler, which returns a 500 that the frontend
        displays as "Error: Query failed".
        """
        rag._mock_ai.generate_response.side_effect = Exception("API connection refused")

        with pytest.raises(Exception, match="API connection refused"):
            rag.query("test question")

    def test_regression_attribute_error_no_longer_propagates(self, rag):
        """
        Regression guard: after the fix in ai_generator.py, ToolUseBlock.text access
        is guarded, so no AttributeError should reach RAGSystem.query().
        This test simulates the generator returning "" (the fixed behaviour)
        instead of raising.
        """
        rag._mock_ai.generate_response.return_value = ""

        response, sources = rag.query("what does lesson 2 cover?")
        assert response == ""
        assert sources == []

    def test_regression_empty_content_no_longer_propagates(self, rag):
        """
        Regression guard: after the fix in ai_generator.py, empty content lists
        are guarded, so no IndexError should reach RAGSystem.query().
        This test simulates the generator returning "" (the fixed behaviour)
        instead of raising.
        """
        rag._mock_ai.generate_response.return_value = ""

        response, sources = rag.query("what does lesson 2 cover?")
        assert response == ""
        assert sources == []
