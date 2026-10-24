# AI trip explanations

PadungGo implements application AI through **Explain this trip** in Trip details. It is optional and runs when requested. The deterministic planner continues to work when the provider is absent or unavailable.

## How it works

1. The browser sends the original search and selected ride occurrence identifiers.
2. The server recomputes the plan and locates those rides, rejecting a stale or unmatched selection.
3. It creates minimal facts: route codes, public boarding, hop-off and transfer stop names, travel order, and a scarce-route flag. Fares, ride or waiting times, distances, route names, the historic-data flag, coordinates and typed place-search text are not sent, so the model cannot repeat or misstate what the screen already shows.
4. The provider writes a short, cheerful summary in plain words (about 30 to 55 words). Code checks route order, hop-off and transfer stops, any price, time, distance or count the model was never given, and unsupported claims, then accepts the text or retries once.
5. The response supplies an AI label, model name, and separate server-written notices. The app shows the text in a collapsible card that keeps the AI-generated label visible, plus one short reminder when routes come from older records; it does not print the notices list. Failure leaves the itinerary unchanged.

These checks reduce mistakes; they do not prove the answer correct. Public stop names can still reveal a journey area. Review the [privacy notes](SECURITY.md).

## Model and configuration

The configured deployment uses GroqCloud's `openai/gpt-oss-20b`. The [model card](https://huggingface.co/openai/gpt-oss-20b) identifies its open weights and Apache 2.0 license; [Groq's documentation](https://console.groq.com/docs/model/openai/gpt-oss-20b) describes the hosted model. Model licensing and hosting terms are separate from PadungGo's MIT license.

Set these on the backend only:

```text
AI_BASE_URL=https://api.groq.com/openai/v1
AI_MODEL=openai/gpt-oss-20b
AI_API_KEY=<server-side secret>
```

The provider client requires HTTPS, except loopback HTTP in debug mode. It uses an OpenAI-compatible HTTP interface; no Laravel SDK is involved. The application does not automatically enforce a replacement model's license. If changing the model for an event requiring open weights, check the replacement's actual license and model identity.

| Setting | Default and meaning |
|---|---|
| `AI_TIMEOUT_SECONDS` | 10 seconds per provider request |
| `AI_MAX_OUTPUT_TOKENS` | 1200, including provider reasoning-token effects |
| `AI_REASONING_EFFORT` | `low`; blank omits the parameter |
| `AI_DAILY_REQUEST_LIMIT` | 800 provider calls per UTC day, using a database counter |
| `AI_CACHE_SECONDS` | 86400 seconds for accepted explanations |
| `DRF_EXPLAIN_THROTTLE` | 6 requests/minute per client per process |

A failed output can cause a second provider call; each call consumes budget. Identical model/prompt-version/facts reuse an accepted cached answer. Default caches and client limits are process-local, while the daily counter is shared through the database. These are application settings, not promises about a hosting account's changing quotas. There is no separate per-person daily allowance.

## Meaningful limitations

- AI does not select routes, establish current service, determine vehicle availability, or verify fares.
- The passenger category and vehicle choices used for frontend guide estimates are not sent to the explanation endpoint. The supported backend fare can remain unknown while the interface shows an approximate guide estimate.
- Waiting and complete journey times are unknown. The summary does not mention them. The server still returns the planner's notices, and the app keeps its own on-screen warnings and the older-records reminder even though the prose omits them.
- Regex and other output checks can reject useful answers or miss misleading language. A working sample is not a reliability evaluation across all trips.
- A network/data change can make the original selection no longer match the recomputed top 50 options.

The [API guide](API_DESIGN.md#explain-this-trip-ai-explanation) documents response states. The [dated review](REVIEW_2026-10-24.md) records a real hosted explanation, rather than only mocked tests.
