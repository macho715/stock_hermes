# News sentiment — user prompt (v1)

Ticker: {{ ticker }}
As-of (UTC): {{ as_of }}

## Recent headlines

{% for item in headlines %}
- ({{ item.source }}) {{ item.title }} — {{ item.url }}
  {% if item.summary %}{{ item.summary }}{% endif %}
{% endfor %}

Return the JSON object as specified by the system prompt.
