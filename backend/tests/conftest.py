import sys
import os

# Ensure backend/ is on the path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import anthropic
from unittest.mock import MagicMock
from vector_store import SearchResults


def _make_usage():
    return anthropic.types.Usage(input_tokens=10, output_tokens=20)


@pytest.fixture
def make_end_turn_response():
    """Factory: build an Anthropic Message with a TextBlock and stop_reason='end_turn'."""
    def _factory(text="Test response"):
        return anthropic.types.Message(
            id="msg_end_turn",
            content=[anthropic.types.TextBlock(type="text", text=text)],
            model="claude-sonnet-4-20250514",
            role="assistant",
            stop_reason="end_turn",
            stop_sequence=None,
            type="message",
            usage=_make_usage(),
        )
    return _factory


@pytest.fixture
def make_tool_use_response():
    """Factory: build an Anthropic Message with a ToolUseBlock and stop_reason='tool_use'."""
    def _factory(tool_name="search_course_content", tool_id="toolu_01", input_dict=None):
        if input_dict is None:
            input_dict = {"query": "test query"}
        return anthropic.types.Message(
            id="msg_tool_use",
            content=[
                anthropic.types.ToolUseBlock(
                    type="tool_use",
                    id=tool_id,
                    name=tool_name,
                    input=input_dict,
                )
            ],
            model="claude-sonnet-4-20250514",
            role="assistant",
            stop_reason="tool_use",
            stop_sequence=None,
            type="message",
            usage=_make_usage(),
        )
    return _factory


@pytest.fixture
def make_empty_content_response():
    """Factory: build an Anthropic Message with an empty content list (edge-case crash trigger)."""
    def _factory(stop_reason="end_turn"):
        return anthropic.types.Message(
            id="msg_empty",
            content=[],
            model="claude-sonnet-4-20250514",
            role="assistant",
            stop_reason=stop_reason,
            stop_sequence=None,
            type="message",
            usage=_make_usage(),
        )
    return _factory


@pytest.fixture
def mock_vector_store():
    """A MagicMock VectorStore pre-configured with one happy-path search result."""
    mock = MagicMock()
    mock.search.return_value = SearchResults(
        documents=["Sample lesson content about Python"],
        metadata=[{"course_title": "Python Basics", "lesson_number": 1}],
        distances=[0.15],
    )
    mock.get_lesson_link.return_value = None
    return mock


@pytest.fixture
def sample_search_results():
    return SearchResults(
        documents=["Content A about loops", "Content B about functions"],
        metadata=[
            {"course_title": "Python Basics", "lesson_number": 1},
            {"course_title": "Python Basics", "lesson_number": 2},
        ],
        distances=[0.1, 0.3],
    )


@pytest.fixture
def empty_search_results():
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def error_search_results():
    return SearchResults(
        documents=[],
        metadata=[],
        distances=[],
        error="Search error: collection not found",
    )
