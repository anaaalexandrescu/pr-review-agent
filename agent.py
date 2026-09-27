"""
Repo Health Check — client/agent using the Google Gemini API.
"""

import asyncio
import os
import re

from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = "gemini-3.5-flash-lite"

SYSTEM_PROMPT = """
You are a rigorous Senior Software Engineer and Security Reviewer.
When asked to review a PR:
1. Call `get_pr_diff` to read the code changes.
2. Analyze the code, identifying: logic bugs, potential security vulnerabilities, missing error handling, or style violations.
3. Format a clear review in Markdown, with concrete code suggestions.
4. If the user asked you to publish the comment or finalize the review, call `post_pr_comment` to post it directly on GitHub.
"""

def mcp_tool_to_gemini(tool):
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.input_schema,
    }

async def run_agent(user_question: str):
    gemini_client = genai.Client()

    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env=dict(os.environ),
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools_response = await session.list_tools()
            function_declarations = [mcp_tool_to_gemini(t) for t in tools_response.tools]
            gemini_tool = types.Tool(function_declarations=function_declarations)

            contents = [types.Content(role="user", parts=[types.Part(text=user_question)])]

            while True:
                await asyncio.sleep(2)

                response = None
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        response = gemini_client.models.generate_content(
                            model=MODEL,
                            contents=contents,
                            config=types.GenerateContentConfig(
                                tools=[gemini_tool],
                                system_instruction=SYSTEM_PROMPT,
                            ),
                        )
                        break
                    except Exception as e:
                        err_str = str(e)
                        if ("503" in err_str or "429" in err_str) and attempt < max_retries - 1:
                            wait_seconds = 60 if "429" in err_str else (attempt + 1) * 4
                            match = re.search(r"retry in (\d+)", err_str)
                            if match:
                                wait_seconds = int(match.group(1)) + 2

                            print(f"  [Server busy / Rate limit]. Waiting {wait_seconds}s before retry (attempt {attempt + 1}/{max_retries})...")
                            await asyncio.sleep(wait_seconds)
                        else:
                            raise e

                candidate = response.candidates[0]
                function_calls = [
                    part.function_call for part in candidate.content.parts
                    if part.function_call
                ]

                contents.append(candidate.content)

                if not function_calls:
                    final_text = "".join(
                        part.text for part in candidate.content.parts if part.text
                    )
                    return final_text

                function_response_parts = []
                for fc in function_calls:
                    print(f"Gemini is calling: {fc.name}({dict(fc.args)})")

                    result = await session.call_tool(fc.name, arguments=dict(fc.args))
                    result_text = "".join(
                        c.text for c in result.content if hasattr(c, "text")
                    )

                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=fc.name,
                            response={"result": result_text},
                        )
                    )

                contents.append(types.Content(role="user", parts=function_response_parts))


async def main():
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: set the GEMINI_API_KEY environment variable before running")
        return

    question = input("Your question (e.g. 'Check the health of the repo anaaalexandrescu/Movie-Preference-Prediction-System'): ")
    answer = await run_agent(question)
    print("\nFinal answer")
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())