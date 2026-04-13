# Agentic Price Optimizer

## What Changed

- Replaced the simple linear graph with a supervisor-driven workflow.
- Added LLM-based query extraction for product, filters, and budget.
- Added Google Shopping search plus optional Google Lens enrichment from a public image URL.
- Added ranking, stats, and final recommendation using the same Gemini model.
- Added a FastAPI backend with a modern streaming frontend in HTML, CSS, and JS.

## Environment

Set:

- `GOOGLE_API_KEY`
- `SERPAPI_API_KEY`

You can place them in:

- [.env](/Users/akshaysrivastava/langgraph/02-price-optimizer/.env)

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn app:app --reload
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Notes

- Google Lens requires a public image URL that SerpAPI can reach.
- The same Gemini client is used for extraction, supervisor routing, ranking, and recommendation.
