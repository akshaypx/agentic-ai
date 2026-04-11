For more info - https://ai.google.dev/gemini-api/docs/langgraph-example


# reAct-agent

This folder contains a small example of a ReAct-style agent built with
langgraph + a Google Gemini (Gemini API) / LangChain-compatible LLM. The
example demonstrates how to wire up a stateful graph that alternates between
calling an LLM and calling tools (a weather tool in this example).

Contents
- `workflow.ipynb` — Jupyter notebook with a step-by-step demo and
  visualization of the ReAct-style agent.

Key concepts
- AgentState: a TypedDict holding the conversation `messages` and `number_of_steps`.
- Tools: functions decorated with `@tool(...)` (the example includes
  `get_weather_forecast` which uses Open-Meteo via geopy for geocoding).
- StateGraph: a simple graph that alternates between `llm` and `tools` nodes
  until the LLM stops requesting tool calls.

Prerequisites
- Python 3.10+ (or whichever your project's runtime uses)
- A Google/Gemini API key if you want to use the Gemini model used in the
  example.

Install (minimal)
1. Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install the minimal dependencies used in the example:

```bash
pip install langgraph langchain-google-genai geopy requests pydantic
```

If your project already pins dependencies, prefer using the project's
requirements/lockfile.

Environment variables
- GEMINI_API_KEY — your Google/Gemini API key. The example reads this from
  the environment. Export it in your shell before running the script or
  notebook:

```bash
export GEMINI_API_KEY="ya29.your_key_here"
```

Running the examples

Notebook (recommended for step-through):
- Open `workflow.ipynb` in Jupyter or VS Code and run the cells. The notebook
  shows how to: create the AgentState, define the weather tool, bind the LLM,
  construct nodes and edges, compile the graph, visualize it, and stream an
  example run.

What the example does
- Defines a `get_weather_forecast` tool that geocodes a location and calls
  the Open-Meteo API to return hourly temperatures for a date.
- Creates a `ChatGoogleGenerativeAI` LLM client (Gemini model) and binds the
  tool to the model, allowing the model to request the tool during inference.
- Builds a `StateGraph` with two nodes: `llm` and `tools`. The graph runs by
  invoking the LLM; if the LLM requests tools, the graph invokes the tool
  node and continues until no tool calls are requested.

Notes & troubleshooting
- The geopy Nominatim geocoder is rate-limited; for heavy usage use a paid
  geocoding provider or cache results.
- If you get errors from the Gemini/Google client, check that `GEMINI_API_KEY`
  is correct and that the `langchain-google-genai` client supports your
  chosen model and params (APIs evolve rapidly).
- The Open-Meteo API is public but may have request/format changes. Inspect
  the JSON returned by `requests` if you see parsing errors.

Security
- Do not commit your API keys to source control. Use environment variables or
  a secret manager.

Next steps / ideas
- Add a requirements.txt or pyproject.toml to pin dependencies.
- Replace Nominatim with an API-key-based geocoding service for production.
- Add unit tests for the tool function and a small integration test that
  exercises the graph stream API.

References
- `workflow.ipynb` — interactive walkthrough (this folder)
