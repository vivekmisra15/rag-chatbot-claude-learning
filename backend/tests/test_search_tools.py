"""
Tests for CourseSearchTool.execute() and ToolManager.

Covers:
- Happy path formatting
- Filter passthrough (course_name, lesson_number)
- Empty results messaging
- Error result handling
- last_sources tracking (plain text and HTML links)
- ToolManager registration, dispatch, and source management
"""

import pytest
from unittest.mock import MagicMock, call
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool(mock_vs):
    return CourseSearchTool(vector_store=mock_vs)


# ---------------------------------------------------------------------------
# CourseSearchTool.execute()
# ---------------------------------------------------------------------------


class TestCourseSearchToolExecute:

    def test_execute_basic_query_returns_formatted_string(self, mock_vector_store):
        tool = _make_tool(mock_vector_store)
        result = tool.execute(query="what is a variable")

        assert "[Python Basics - Lesson 1]" in result
        assert "Sample lesson content about Python" in result

    def test_execute_calls_search_with_correct_args(self, mock_vector_store):
        tool = _make_tool(mock_vector_store)
        tool.execute(query="what is a variable")

        mock_vector_store.search.assert_called_once_with(
            query="what is a variable",
            course_name=None,
            lesson_number=None,
        )

    def test_execute_with_course_name_filter_passes_filter_to_store(self, mock_vector_store):
        tool = _make_tool(mock_vector_store)
        tool.execute(query="variables", course_name="Python Basics")

        mock_vector_store.search.assert_called_once_with(
            query="variables",
            course_name="Python Basics",
            lesson_number=None,
        )

    def test_execute_with_lesson_number_filter_passes_filter_to_store(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=["content about tools"],
            metadata=[{"course_title": "MCP Course", "lesson_number": 3}],
            distances=[0.2],
        )
        tool = _make_tool(mock_vector_store)
        result = tool.execute(query="tools", lesson_number=3)

        mock_vector_store.search.assert_called_once_with(
            query="tools",
            course_name=None,
            lesson_number=3,
        )
        assert "Lesson 3" in result

    def test_execute_empty_results_returns_no_content_message(
        self, mock_vector_store, empty_search_results
    ):
        mock_vector_store.search.return_value = empty_search_results
        tool = _make_tool(mock_vector_store)
        result = tool.execute(query="nonexistent topic")

        assert result == "No relevant content found."

    def test_execute_empty_results_with_course_filter_includes_filter_in_message(
        self, mock_vector_store, empty_search_results
    ):
        mock_vector_store.search.return_value = empty_search_results
        tool = _make_tool(mock_vector_store)
        result = tool.execute(query="x", course_name="Python Basics")

        assert result == "No relevant content found in course 'Python Basics'."

    def test_execute_empty_results_with_lesson_filter_includes_lesson_in_message(
        self, mock_vector_store, empty_search_results
    ):
        mock_vector_store.search.return_value = empty_search_results
        tool = _make_tool(mock_vector_store)
        result = tool.execute(query="x", lesson_number=2)

        assert result == "No relevant content found in lesson 2."

    def test_execute_search_error_returns_error_string(
        self, mock_vector_store, error_search_results
    ):
        mock_vector_store.search.return_value = error_search_results
        tool = _make_tool(mock_vector_store)
        result = tool.execute(query="anything")

        assert result == "Search error: collection not found"

    def test_execute_sets_last_sources_plain_text_when_no_link(self, mock_vector_store):
        mock_vector_store.get_lesson_link.return_value = None
        tool = _make_tool(mock_vector_store)
        tool.execute(query="test")

        assert tool.last_sources == ["Python Basics - Lesson 1"]

    def test_execute_sets_last_sources_html_link_when_link_available(self, mock_vector_store):
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson/1"
        tool = _make_tool(mock_vector_store)
        tool.execute(query="test")

        assert len(tool.last_sources) == 1
        src = tool.last_sources[0]
        assert 'href="https://example.com/lesson/1"' in src
        assert "Python Basics - Lesson 1" in src
        assert "<a " in src

    def test_execute_multiple_results_sets_multiple_sources(
        self, mock_vector_store, sample_search_results
    ):
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = None
        tool = _make_tool(mock_vector_store)
        tool.execute(query="test")

        assert len(tool.last_sources) == 2

    def test_execute_result_without_lesson_number_omits_lesson_from_header(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=["general content"],
            metadata=[{"course_title": "Some Course"}],  # no lesson_number key
            distances=[0.1],
        )
        tool = _make_tool(mock_vector_store)
        result = tool.execute(query="test")

        assert "[Some Course]" in result
        assert "Lesson" not in result
        mock_vector_store.get_lesson_link.assert_not_called()

    def test_execute_no_course_name_in_metadata_uses_unknown(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=["some content"],
            metadata=[{}],  # completely empty metadata
            distances=[0.1],
        )
        tool = _make_tool(mock_vector_store)
        result = tool.execute(query="test")

        assert "[unknown]" in result

    def test_execute_clears_previous_sources_on_new_call(self, mock_vector_store):
        mock_vector_store.get_lesson_link.return_value = None
        tool = _make_tool(mock_vector_store)

        tool.execute(query="first query")
        assert len(tool.last_sources) == 1

        tool.execute(query="second query")
        # Should still be 1, not 2 accumulated
        assert len(tool.last_sources) == 1


# ---------------------------------------------------------------------------
# ToolManager
# ---------------------------------------------------------------------------


class TestToolManager:

    def _make_mock_tool(self, name="search_course_content", return_value="tool output"):
        mock_tool = MagicMock()
        mock_tool.get_tool_definition.return_value = {"name": name}
        mock_tool.execute.return_value = return_value
        mock_tool.last_sources = []
        return mock_tool

    def test_register_and_execute_tool(self):
        tm = ToolManager()
        mock_tool = self._make_mock_tool()
        tm.register_tool(mock_tool)

        result = tm.execute_tool("search_course_content", query="test")

        mock_tool.execute.assert_called_once_with(query="test")
        assert result == "tool output"

    def test_execute_unknown_tool_returns_not_found_message(self):
        tm = ToolManager()
        result = tm.execute_tool("nonexistent_tool")

        assert result == "Tool 'nonexistent_tool' not found"

    def test_get_tool_definitions_returns_all_definitions(self):
        tm = ToolManager()
        mock_tool = self._make_mock_tool()
        tm.register_tool(mock_tool)

        defs = tm.get_tool_definitions()

        assert defs == [{"name": "search_course_content"}]

    def test_get_last_sources_returns_sources_from_registered_tool(self):
        tm = ToolManager()
        mock_tool = self._make_mock_tool()
        mock_tool.last_sources = ["Source 1", "Source 2"]
        tm.register_tool(mock_tool)

        assert tm.get_last_sources() == ["Source 1", "Source 2"]

    def test_get_last_sources_returns_empty_when_no_sources(self):
        tm = ToolManager()
        mock_tool = self._make_mock_tool()
        mock_tool.last_sources = []
        tm.register_tool(mock_tool)

        assert tm.get_last_sources() == []

    def test_reset_sources_clears_all_tool_sources(self):
        tm = ToolManager()
        mock_tool = self._make_mock_tool()
        mock_tool.last_sources = ["Source 1"]
        tm.register_tool(mock_tool)

        tm.reset_sources()

        assert mock_tool.last_sources == []

    def test_register_tool_without_name_raises_value_error(self):
        tm = ToolManager()
        bad_tool = MagicMock()
        bad_tool.get_tool_definition.return_value = {}  # no 'name' key

        with pytest.raises(ValueError):
            tm.register_tool(bad_tool)
