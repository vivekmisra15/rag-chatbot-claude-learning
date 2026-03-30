"""
Tests for AIGenerator.generate_response() and _handle_tool_execution().

Covers:
- Direct (end_turn) response path
- Tool-use response path (two-call pattern)
- Conversation history handling
- Verified crash paths that produce "Query failed" (marked BUG)
"""
import pytest
import anthropic
from unittest.mock import MagicMock, patch, call
from ai_generator import AIGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_generator(api_key="fake_key", model="claude-sonnet-4-20250514"):
    with patch("ai_generator.anthropic.Anthropic"):
        gen = AIGenerator(api_key=api_key, model=model)
    return gen


def _make_usage():
    return anthropic.types.Usage(input_tokens=10, output_tokens=20)


def _make_end_turn(text="Direct answer"):
    return anthropic.types.Message(
        id="msg_end",
        content=[anthropic.types.TextBlock(type="text", text=text)],
        model="claude-sonnet-4-20250514",
        role="assistant",
        stop_reason="end_turn",
        stop_sequence=None,
        type="message",
        usage=_make_usage(),
    )


def _make_tool_use(query="search term", course_name=None, tool_id="toolu_01"):
    input_dict = {"query": query}
    if course_name:
        input_dict["course_name"] = course_name
    return anthropic.types.Message(
        id="msg_tool",
        content=[
            anthropic.types.ToolUseBlock(
                type="tool_use",
                id=tool_id,
                name="search_course_content",
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


def _make_empty_content(stop_reason="end_turn"):
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


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestAIGeneratorInit:

    def test_init_sets_model(self):
        gen = _make_generator(model="claude-sonnet-4-20250514")
        assert gen.model == "claude-sonnet-4-20250514"

    def test_init_base_params_temperature_zero(self):
        gen = _make_generator()
        assert gen.base_params["temperature"] == 0

    def test_init_base_params_max_tokens(self):
        gen = _make_generator()
        assert gen.base_params["max_tokens"] == 800


# ---------------------------------------------------------------------------
# Direct (end_turn) response path
# ---------------------------------------------------------------------------

class TestGenerateResponseDirectPath:

    def test_end_turn_response_returns_text(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_end_turn("Hello world")

        result = gen.generate_response(query="What is Python?")

        assert result == "Hello world"

    def test_without_tools_does_not_include_tools_in_api_call(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_end_turn()

        gen.generate_response(query="test")

        call_kwargs = gen.client.messages.create.call_args[1]
        assert "tools" not in call_kwargs
        assert "tool_choice" not in call_kwargs

    def test_with_tools_includes_tools_and_tool_choice(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_end_turn()
        tools = [{"name": "search_course_content"}]
        mock_tm = MagicMock()

        gen.generate_response(query="test", tools=tools, tool_manager=mock_tm)

        call_kwargs = gen.client.messages.create.call_args[1]
        assert call_kwargs["tools"] == tools
        assert call_kwargs["tool_choice"] == {"type": "auto"}

    def test_with_conversation_history_appends_to_system_prompt(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_end_turn()

        gen.generate_response(query="follow-up", conversation_history="User: hi\nAssistant: hello")

        call_kwargs = gen.client.messages.create.call_args[1]
        assert "Previous conversation:" in call_kwargs["system"]
        assert "User: hi" in call_kwargs["system"]

    def test_without_conversation_history_uses_base_system_prompt_only(self):
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_end_turn()

        gen.generate_response(query="test")

        call_kwargs = gen.client.messages.create.call_args[1]
        assert call_kwargs["system"] == AIGenerator.SYSTEM_PROMPT
        assert "Previous conversation:" not in call_kwargs["system"]

    # --- BUG TESTS: these expose the crash paths causing "Query failed" ---

    def test_tool_use_stop_reason_without_tool_manager_returns_empty_string(self):
        """
        FIX for BUG #1: When Claude returns stop_reason='tool_use' but tool_manager=None,
        the fixed code checks hasattr(.text) before accessing it, returning "" safely
        instead of raising AttributeError.
        """
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_tool_use()

        result = gen.generate_response(query="course question", tools=[{"name": "search"}], tool_manager=None)
        assert result == ""

    def test_empty_content_list_returns_empty_string(self):
        """
        FIX for BUG #2: When the API returns an empty content list, the fixed
        code guards with `if response.content` and returns "" instead of
        raising IndexError.
        """
        gen = _make_generator()
        gen.client.messages.create.return_value = _make_empty_content(stop_reason="end_turn")

        result = gen.generate_response(query="test")
        assert result == ""


# ---------------------------------------------------------------------------
# Tool execution (two-call pattern)
# ---------------------------------------------------------------------------

class TestHandleToolExecution:

    def _setup(self, first_response, second_response, tool_result="Search results text"):
        gen = _make_generator()
        gen.client.messages.create.side_effect = [first_response, second_response]

        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = tool_result
        tool_manager.get_tool_definitions.return_value = [{"name": "search_course_content"}]

        return gen, tool_manager

    def test_tool_execution_calls_tool_manager_with_correct_args(self):
        first = _make_tool_use(query="python loops", course_name="Python Basics", tool_id="toolu_01")
        second = _make_end_turn("Here is info")
        gen, tm = self._setup(first, second)

        gen.generate_response(
            query="tell me about python loops",
            tools=[{"name": "search_course_content"}],
            tool_manager=tm,
        )

        tm.execute_tool.assert_called_once_with(
            "search_course_content",
            query="python loops",
            course_name="Python Basics",
        )

    def test_tool_execution_second_call_has_no_tools_param(self):
        first = _make_tool_use()
        second = _make_end_turn("Final answer")
        gen, tm = self._setup(first, second)

        gen.generate_response(query="test", tools=[{"name": "search"}], tool_manager=tm)

        second_call_kwargs = gen.client.messages.create.call_args_list[1][1]
        assert "tools" not in second_call_kwargs

    def test_tool_execution_returns_final_response_text(self):
        first = _make_tool_use()
        second = _make_end_turn("The final answer")
        gen, tm = self._setup(first, second)

        result = gen.generate_response(query="test", tools=[{"name": "search"}], tool_manager=tm)

        assert result == "The final answer"

    def test_tool_execution_appends_tool_result_as_user_message(self):
        first = _make_tool_use(tool_id="toolu_42")
        second = _make_end_turn("answer")
        gen, tm = self._setup(first, second, tool_result="Search content here")

        gen.generate_response(query="test", tools=[{"name": "search"}], tool_manager=tm)

        second_call_kwargs = gen.client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]

        # 3 messages: original user, assistant tool_use, user tool_result
        assert len(messages) == 3
        assert messages[2]["role"] == "user"
        tool_result_block = messages[2]["content"][0]
        assert tool_result_block["type"] == "tool_result"
        assert tool_result_block["tool_use_id"] == "toolu_42"
        assert tool_result_block["content"] == "Search content here"

    def test_tool_execution_multiple_tool_calls_all_executed(self):
        """Multiple ToolUseBlocks in one response should all be dispatched."""
        first = anthropic.types.Message(
            id="msg_multi",
            content=[
                anthropic.types.ToolUseBlock(
                    type="tool_use", id="toolu_01", name="search_course_content",
                    input={"query": "query A"},
                ),
                anthropic.types.ToolUseBlock(
                    type="tool_use", id="toolu_02", name="search_course_content",
                    input={"query": "query B"},
                ),
            ],
            model="claude-sonnet-4-20250514",
            role="assistant",
            stop_reason="tool_use",
            stop_sequence=None,
            type="message",
            usage=_make_usage(),
        )
        second = _make_end_turn("Combined answer")
        gen, tm = self._setup(first, second)

        gen.generate_response(query="test", tools=[{"name": "search"}], tool_manager=tm)

        assert tm.execute_tool.call_count == 2
        second_call_kwargs = gen.client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]
        tool_results_msg = messages[-1]
        assert len(tool_results_msg["content"]) == 2

    def test_no_tool_use_blocks_skips_tool_result_message(self):
        """
        Edge case: stop_reason='tool_use' but content has no ToolUseBlock.
        The `if tool_results:` guard (line 123) prevents appending an empty
        user message. The second API call is made with only 2 messages
        (original user + assistant) rather than 3. No crash occurs, but
        no search results are provided to Claude in the follow-up.
        """
        # stop_reason="tool_use" but content only has a TextBlock (no ToolUseBlock)
        bad_first = anthropic.types.Message(
            id="msg_bad",
            content=[anthropic.types.TextBlock(type="text", text="hmm")],
            model="claude-sonnet-4-20250514",
            role="assistant",
            stop_reason="tool_use",
            stop_sequence=None,
            type="message",
            usage=_make_usage(),
        )
        second = _make_end_turn("answer")
        gen, tm = self._setup(bad_first, second)

        result = gen.generate_response(query="test", tools=[{"name": "search"}], tool_manager=tm)

        # No tool was executed
        tm.execute_tool.assert_not_called()

        # Second API call was still made (the guard skips appending, not the whole call)
        assert gen.client.messages.create.call_count == 2

        # Second call has 2 messages only (no tool-result user message appended)
        second_call_kwargs = gen.client.messages.create.call_args_list[1][1]
        assert len(second_call_kwargs["messages"]) == 2

        # And the final answer is still returned
        assert result == "answer"

    def test_final_response_empty_content_returns_empty_string(self):
        """
        FIX for BUG #4: If the second Claude call returns empty content,
        the fixed code guards and returns "" instead of raising IndexError
        at 'final_response.content[0].text'.
        """
        first = _make_tool_use()
        empty_second = _make_empty_content(stop_reason="end_turn")
        gen, tm = self._setup(first, empty_second)

        result = gen.generate_response(query="test", tools=[{"name": "search"}], tool_manager=tm)
        assert result == ""
