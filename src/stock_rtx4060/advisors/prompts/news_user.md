Ticker: {{ ticker }}
As of: {{ as_of }}

{% if notebook_analysis %}
## NotebookLM source-grounded analysis

- Sentiment: {{ notebook_analysis.sentiment }} (score={{ notebook_analysis.sentiment_score }})
- Market impact: {{ notebook_analysis.market_impact }}
- Confidence: {{ notebook_analysis.confidence }}
- Summary: {{ notebook_analysis.summary }}
- Bullish factors: {{ notebook_analysis.bullish_factors | join("; ") }}
- Bearish factors: {{ notebook_analysis.bearish_factors | join("; ") }}
- LLM instruction: {{ notebook_analysis.recommended_llm_instruction }}
{% endif %}

## Recent headlines

{% for item in headlines %}
- ({{ item.source }}) {{ item.title }} — {{ item.url }}
  {% if item.summary %}{{ item.summary }}{% endif %}
{% endfor %}

Task:
Return ONLY valid JSON:
{
  "score": -1.0..1.0,
  "confidence": 0.0..1.0,
  "rationale": "explain how NotebookLM analysis and price context affect the stock view",
  "citations": ["source URLs"],
  "proposition": "single falsifiable market proposition"
}

Rules:
- If NotebookLM confidence is low, reduce your confidence.
- If price momentum contradicts news sentiment, state the conflict.
- Do not upgrade recommendation gates. This is advisory only.
