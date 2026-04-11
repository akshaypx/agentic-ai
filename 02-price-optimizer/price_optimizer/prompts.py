from langchain_core.prompts import ChatPromptTemplate

pricing_prompt = ChatPromptTemplate.from_template("""
You are a pricing strategist for e-commerce.

Return ONLY valid JSON. No markdown. No explanation outside JSON.

DATA:
- Query: {query}
- Prices: {prices}
- Avg Price: {avg_price}
- Min Price: {min_price}
- Max Price: {max_price}

OUTPUT FORMAT:
{{
  "recommended_price": number,
  "reasoning": "short explanation"
}}
""")