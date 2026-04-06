# LLM Providers

## How the AI Layer Works

All content generation flows through `apps/api/app/services/content_generator.py`.

The function `_call_model()` dispatches based on `DEFAULT_MODEL_PROVIDER` in `.env`:

```python
async def _call_model(system: str, user: str) -> dict:
    if settings.default_model_provider == "anthropic":
        return await _call_anthropic(system, user)
    return await _call_openai(system, user)
```

To add a new provider, add a new `_call_<provider>()` function and a branch in `_call_model()`.

---

## Built-in Providers

### Anthropic (Claude) — default
- Env var: `ANTHROPIC_API_KEY`
- Model: `DEFAULT_EXTERNAL_MODEL=claude-sonnet-4-6`
- SDK: `anthropic` Python package
- Best for: Long-form content, instruction following, brand voice

### OpenAI (GPT-4o) — fallback
- Env var: `OPENAI_API_KEY`
- Model: hardcoded to `gpt-4o` in `_call_openai()`
- SDK: `openai` Python package
- Set `DEFAULT_MODEL_PROVIDER=openai` to use

---

## Adding Moonshot AI (Kimi)

Moonshot AI's API is OpenAI-compatible, so you can use the OpenAI SDK pointed at their endpoint:

**1. Add to `.env`:**
```
MOONSHOT_API_KEY=sk-...
MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
DEFAULT_MODEL_PROVIDER=moonshot
DEFAULT_EXTERNAL_MODEL=moonshot-v1-8k
```

**2. Add to `apps/api/app/config.py`:**
```python
moonshot_api_key: str = ""
moonshot_base_url: str = "https://api.moonshot.cn/v1"
```

**3. Add to `apps/api/app/services/content_generator.py`:**
```python
async def _call_moonshot(system: str, user: str) -> dict[str, Any]:
    client = openai.AsyncOpenAI(
        api_key=settings.moonshot_api_key,
        base_url=settings.moonshot_base_url,
    )
    response = await client.chat.completions.create(
        model=settings.default_external_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"content": raw}
```

**4. Update `_call_model()`:**
```python
async def _call_model(system: str, user: str) -> dict[str, Any]:
    if settings.default_model_provider == "anthropic":
        return await _call_anthropic(system, user)
    if settings.default_model_provider == "moonshot":
        return await _call_moonshot(system, user)
    return await _call_openai(system, user)
```

---

## Any OpenAI-Compatible Provider

The same pattern works for: Groq, Together AI, Fireworks AI, DeepSeek, Mistral, local Ollama, etc.
Just point the OpenAI client at their `base_url` and set the right model name.

---

## Data Classification Rules

**Never send to any external LLM:**
- PHI (health data)
- PII (names, emails, phones) — unless explicitly redacted
- API keys, passwords, secrets
- Customer lists

See `references/06-data-classification.md` for the full rules.
The policy checker runs before generation: `apps/api/app/services/policy.py`

---

## Private Model Plane (Phase 3)

For PHI-safe generation, Phase 3 adds a private model plane:
- vLLM or SGLang running open-weight models inside a VPC
- A second provider branch `DEFAULT_MODEL_PROVIDER=private`
- Data classification middleware that auto-routes based on content sensitivity
