# Devil's advocate — user prompt (v1)

Ticker: {{ ticker }}
As-of (UTC): {{ as_of }}

## Factor values
{% for k, v in factors.items() %}
- {{ k }}: {{ v }}
{% endfor %}

## SHAP attributions (top features by |contribution|)
{% for feat, attrib in shap.items() %}
- {{ feat }}: {{ attrib }}
{% endfor %}

## Bull-case summary
{{ bull_summary }}

Return the JSON object as specified by the system prompt.
