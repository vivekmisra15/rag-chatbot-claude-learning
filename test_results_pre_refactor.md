# Test Results — Pre-Refactor Baseline

**Date:** 2026-03-30
**Branch:** main
**Commit:** dc7239e4
**Run command:** `uv run pytest backend/tests/ -v`

## Summary

```
51 passed in 0.30s
```

## Full Results

| # | Test | Result |
|---|---|---|
| 1 | `test_ai_generator.py::TestAIGeneratorInit::test_init_sets_model` | PASSED |
| 2 | `test_ai_generator.py::TestAIGeneratorInit::test_init_base_params_temperature_zero` | PASSED |
| 3 | `test_ai_generator.py::TestAIGeneratorInit::test_init_base_params_max_tokens` | PASSED |
| 4 | `test_ai_generator.py::TestGenerateResponseDirectPath::test_end_turn_response_returns_text` | PASSED |
| 5 | `test_ai_generator.py::TestGenerateResponseDirectPath::test_without_tools_does_not_include_tools_in_api_call` | PASSED |
| 6 | `test_ai_generator.py::TestGenerateResponseDirectPath::test_with_tools_includes_tools_and_tool_choice` | PASSED |
| 7 | `test_ai_generator.py::TestGenerateResponseDirectPath::test_with_conversation_history_appends_to_system_prompt` | PASSED |
| 8 | `test_ai_generator.py::TestGenerateResponseDirectPath::test_without_conversation_history_uses_base_system_prompt_only` | PASSED |
| 9 | `test_ai_generator.py::TestGenerateResponseDirectPath::test_tool_use_stop_reason_without_tool_manager_returns_empty_string` | PASSED |
| 10 | `test_ai_generator.py::TestGenerateResponseDirectPath::test_empty_content_list_returns_empty_string` | PASSED |
| 11 | `test_ai_generator.py::TestHandleToolExecution::test_tool_execution_calls_tool_manager_with_correct_args` | PASSED |
| 12 | `test_ai_generator.py::TestHandleToolExecution::test_tool_execution_second_call_has_no_tools_param` | PASSED |
| 13 | `test_ai_generator.py::TestHandleToolExecution::test_tool_execution_returns_final_response_text` | PASSED |
| 14 | `test_ai_generator.py::TestHandleToolExecution::test_tool_execution_appends_tool_result_as_user_message` | PASSED |
| 15 | `test_ai_generator.py::TestHandleToolExecution::test_tool_execution_multiple_tool_calls_all_executed` | PASSED |
| 16 | `test_ai_generator.py::TestHandleToolExecution::test_no_tool_use_blocks_skips_tool_result_message` | PASSED |
| 17 | `test_ai_generator.py::TestHandleToolExecution::test_final_response_empty_content_returns_empty_string` | PASSED |
| 18 | `test_rag_system.py::TestRAGSystemQueryPrompt::test_query_wraps_user_input_in_prompt` | PASSED |
| 19 | `test_rag_system.py::TestRAGSystemQueryPrompt::test_query_passes_tool_definitions_to_generator` | PASSED |
| 20 | `test_rag_system.py::TestRAGSystemQuerySession::test_query_without_session_id_passes_none_history` | PASSED |
| 21 | `test_rag_system.py::TestRAGSystemQuerySession::test_query_with_session_id_retrieves_history` | PASSED |
| 22 | `test_rag_system.py::TestRAGSystemQuerySession::test_query_with_session_id_updates_history_after_response` | PASSED |
| 23 | `test_rag_system.py::TestRAGSystemQuerySession::test_query_without_session_id_does_not_update_history` | PASSED |
| 24 | `test_rag_system.py::TestRAGSystemQuerySession::test_query_empty_session_history_passes_none_to_generator` | PASSED |
| 25 | `test_rag_system.py::TestRAGSystemQueryReturnContract::test_query_returns_response_and_sources_tuple` | PASSED |
| 26 | `test_rag_system.py::TestRAGSystemQueryReturnContract::test_query_returns_empty_sources_when_no_tool_used` | PASSED |
| 27 | `test_rag_system.py::TestRAGSystemQueryReturnContract::test_query_resets_sources_after_retrieval` | PASSED |
| 28 | `test_rag_system.py::TestRAGSystemQueryExceptionPropagation::test_query_propagates_exception_to_caller` | PASSED |
| 29 | `test_rag_system.py::TestRAGSystemQueryExceptionPropagation::test_regression_attribute_error_no_longer_propagates` | PASSED |
| 30 | `test_rag_system.py::TestRAGSystemQueryExceptionPropagation::test_regression_empty_content_no_longer_propagates` | PASSED |
| 31 | `test_search_tools.py::TestCourseSearchToolExecute::test_execute_basic_query_returns_formatted_string` | PASSED |
| 32 | `test_search_tools.py::TestCourseSearchToolExecute::test_execute_calls_search_with_correct_args` | PASSED |
| 33 | `test_search_tools.py::TestCourseSearchToolExecute::test_execute_with_course_name_filter_passes_filter_to_store` | PASSED |
| 34 | `test_search_tools.py::TestCourseSearchToolExecute::test_execute_with_lesson_number_filter_passes_filter_to_store` | PASSED |
| 35 | `test_search_tools.py::TestCourseSearchToolExecute::test_execute_empty_results_returns_no_content_message` | PASSED |
| 36 | `test_search_tools.py::TestCourseSearchToolExecute::test_execute_empty_results_with_course_filter_includes_filter_in_message` | PASSED |
| 37 | `test_search_tools.py::TestCourseSearchToolExecute::test_execute_empty_results_with_lesson_filter_includes_lesson_in_message` | PASSED |
| 38 | `test_search_tools.py::TestCourseSearchToolExecute::test_execute_search_error_returns_error_string` | PASSED |
| 39 | `test_search_tools.py::TestCourseSearchToolExecute::test_execute_sets_last_sources_plain_text_when_no_link` | PASSED |
| 40 | `test_search_tools.py::TestCourseSearchToolExecute::test_execute_sets_last_sources_html_link_when_link_available` | PASSED |
| 41 | `test_search_tools.py::TestCourseSearchToolExecute::test_execute_multiple_results_sets_multiple_sources` | PASSED |
| 42 | `test_search_tools.py::TestCourseSearchToolExecute::test_execute_result_without_lesson_number_omits_lesson_from_header` | PASSED |
| 43 | `test_search_tools.py::TestCourseSearchToolExecute::test_execute_no_course_name_in_metadata_uses_unknown` | PASSED |
| 44 | `test_search_tools.py::TestCourseSearchToolExecute::test_execute_clears_previous_sources_on_new_call` | PASSED |
| 45 | `test_search_tools.py::TestToolManager::test_register_and_execute_tool` | PASSED |
| 46 | `test_search_tools.py::TestToolManager::test_execute_unknown_tool_returns_not_found_message` | PASSED |
| 47 | `test_search_tools.py::TestToolManager::test_get_tool_definitions_returns_all_definitions` | PASSED |
| 48 | `test_search_tools.py::TestToolManager::test_get_last_sources_returns_sources_from_registered_tool` | PASSED |
| 49 | `test_search_tools.py::TestToolManager::test_get_last_sources_returns_empty_when_no_sources` | PASSED |
| 50 | `test_search_tools.py::TestToolManager::test_reset_sources_clears_all_tool_sources` | PASSED |
| 51 | `test_search_tools.py::TestToolManager::test_register_tool_without_name_raises_value_error` | PASSED |

## Key contracts these tests enforce

- `CourseSearchTool.execute()` passes `query`, `course_name`, `lesson_number` through to `VectorStore.search()` unchanged
- `CourseSearchTool` returns `"No relevant content found."` (exact string) on empty results; includes filter info when filters were active
- `CourseSearchTool` returns `results.error` verbatim on error results
- `CourseSearchTool.last_sources` is populated with plain text or `<a href>` HTML per call, and reset to `[]` by `ToolManager.reset_sources()`
- `AIGenerator` always sends `tools` + `tool_choice={"type":"auto"}` together, never separately
- `AIGenerator` appends `"Previous conversation:\n{history}"` to the system prompt (not a separate message)
- `AIGenerator` makes exactly 2 API calls when `stop_reason="tool_use"`: first with tools, second without
- Second API call messages structure: `[user, assistant_tool_use, user_tool_result]` (3 items)
- `AIGenerator` returns `""` (not raises) when `content` list is empty or `content[0]` has no `.text`
- `RAGSystem.query()` wraps the user query as `"Answer this question about course materials: {query}"`
- `RAGSystem.query()` calls `get_last_sources()` before `reset_sources()` (order enforced)
- `RAGSystem.query()` calls `add_exchange(session_id, original_query, response)` — not the wrapped prompt
