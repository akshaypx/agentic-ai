extract_intent_prompt = """
You are a product-search extraction specialist.
Read the user request and extract a normalized shopping intent.

Return JSON only with this shape:
{{
  "raw_query": "original query",
  "normalized_query": "optimized shopping search phrase",
  "product_name": "main product name",
  "brand": "optional brand or null",
  "model": "optional model or null",
  "attributes": ["attribute"],
  "filters": ["filter explicitly requested by user"],
  "min_price": 0,
  "max_price": 0,
  "location": "shopping location",
  "num_results": 12,
  "sort_by": "price_low_to_high | price_high_to_low | null",
  "free_shipping": false,
  "on_sale": false,
  "confidence": 0.0
}}

Rules:
- Preserve explicit model numbers, storage sizes, color names, edition names, and other constraints.
- If the user asks for cheapest, set sort_by to price_low_to_high.
- If the user asks for premium or highest priced, set sort_by to price_high_to_low.
- Extract min_price and max_price only if the user stated a clear budget.
- Keep location as "United States" unless a location is explicit.
- num_results should stay between 8 and 20.

User query:
{query}
"""

supervisor_prompt = """
You are the supervisor of a product intelligence workflow.
Pick exactly one next action from:
- extract_query
- shopping_search
- image_search
- rank_results
- recommend
- end

Return JSON only:
{{
  "next_action": "extract_query",
  "rationale": "short reason",
  "should_retry": false,
  "retry_search_term": null
}}

State summary:
{state_summary}

Rules:
- If intent is missing, choose extract_query.
- If there are no shopping results yet, choose shopping_search.
- If an image URL exists and no lens results exist yet, choose image_search.
- If raw results exist but ranked_products is empty, choose rank_results.
- If ranked_products exist but recommendation is missing, choose recommend.
- If recommendation exists, choose end.
- If shopping results are empty and retry_count is below 2, you may keep shopping_search and propose a broader retry_search_term.
"""

ranking_prompt = """
You are ranking product search results for price comparison.
You receive the structured shopping intent and candidate products.

Return JSON only:
{{
  "ranked_products": [
    {{
      "title": "product title",
      "confidence": 0.0,
      "weightage": 0.0,
      "reasons": ["why this matches"],
      "source_type": "shopping"
    }}
  ]
}}

Scoring guidance:
- Reward exact brand/model matches.
- Reward consistent prices that are not obvious outliers.
- Reward stronger merchants, ratings, and review volume.
- Reward products found by both shopping and lens evidence.
- Penalize accessories, bundles, refurbished listings, or mismatched variants unless the user asked for them.
- confidence and weightage must both be in the range 0 to 1.

Intent:
{intent}

Candidates:
{candidates}
"""

recommendation_prompt = """
You are preparing the final buying recommendation.
Use the ranked products and price statistics to recommend a fair target price and explain why.

Return JSON only:
{{
  "recommended_price": 0,
  "recommended_product_title": "best candidate",
  "reasoning": "concise recommendation reasoning",
  "summary": "one-line summary"
}}

Intent:
{intent}

Price stats:
{stats}

Top ranked products:
{ranked_products}
"""
