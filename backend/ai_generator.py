import anthropic
from typing import List, Optional, Dict, Any


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Maximum number of sequential tool-calling rounds per query.
    # After this many rounds the loop exits and a final no-tools call is made.
    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **Up to 2 sequential searches per query** — use a second search only if the first result is insufficient or you need to look up a different aspect of the question
- Prefer answering directly after one search when results are sufficient
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Supports up to MAX_TOOL_ROUNDS sequential tool-calling rounds. Each round
        keeps tools available so Claude can chain a second search when the first
        result is insufficient. After all rounds are exhausted a final no-tools
        call forces a text answer.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        messages = [{"role": "user", "content": query}]

        # Prepare initial API call parameters
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content,
        }
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Round 0 — initial call
        response = self.client.messages.create(**api_params)

        # Sequential tool-calling loop — at most MAX_TOOL_ROUNDS iterations.
        # Each iteration keeps tools active so Claude can chain searches.
        rounds_completed = 0
        while (
            response.stop_reason == "tool_use"
            and tool_manager
            and rounds_completed < self.MAX_TOOL_ROUNDS
        ):
            # Append assistant's tool-use response to the running message history
            messages.append({"role": "assistant", "content": response.content})

            # Execute every tool call block in this response
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = tool_manager.execute_tool(block.name, **block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            rounds_completed += 1

            if rounds_completed < self.MAX_TOOL_ROUNDS:
                # Still within budget: call WITH tools so Claude can search again
                # or give a direct answer
                next_params = {
                    **self.base_params,
                    "messages": messages,
                    "system": system_content,
                    "tools": tools,
                    "tool_choice": {"type": "auto"},
                }
                response = self.client.messages.create(**next_params)
            # rounds_completed == MAX_TOOL_ROUNDS → exit loop; fall through to
            # the forced-text call below

        # If the loop was exhausted (Claude still wants a tool call), force a
        # text answer by making one final call without tools.
        # Guard: only when tool_manager is set — preserves existing behaviour
        # for the tool_manager=None code path.
        if response.stop_reason == "tool_use" and tool_manager:
            final_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content,
            }
            response = self.client.messages.create(**final_params)

        # Return text from whichever response terminated the flow
        if response.content and hasattr(response.content[0], "text"):
            return response.content[0].text
        return ""
