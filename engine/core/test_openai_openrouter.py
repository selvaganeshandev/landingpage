"""
Test script for the ChatGPT → OpenRouter transport switch.

ChatGPT was the last provider still calling its vendor's API directly. It was
held back so the tracked measurement would keep reflecting what a real ChatGPT
user is told — but that rationale was about the MODEL, not the transport:
OpenRouter forwards to the same OpenAI model. Routing it puts every LLM call in
the platform on one balance.

Four things have to hold for the switch to be invisible downstream:

  1. The credential for 'openai' resolves to the OpenRouter key. Per-org OpenAI
     BYOK keys are no longer consulted, exactly like Anthropic's and Perplexity's.
  2. The client is pointed at OpenRouter, never at api.openai.com.
  3. The model slug carries the `openai/` prefix. This is the sharp edge: the
     bare `gpt-4o` the direct OpenAI API took is NOT a valid model id on
     OpenRouter and 404s, so a missed default silently kills ChatGPT tracking.
  4. The internal (cheap) and tracked (flagship) calls stay on DIFFERENT models
     even though they now share a transport. Collapsing them would cheapen the
     measurement itself.

Verified live against openrouter.ai on 2026-07-27: `openai/gpt-4o` is served,
the /responses API is implemented, and tools=[{"type": "web_search"}] is
honoured — the two SDK surfaces process_prompt_with_chatgpt depends on. Web
search is answered by OpenRouter's own `web` plugin rather than OpenAI's native
tool, so grounded answers cite different sources from the cutover onward.

Everything is stubbed (Django, the openai SDK). No network, no database, no
API key required.

Run:  python core/test_openai_openrouter.py     (from the engine/ directory)
"""
import importlib.util
import os
import sys
import types


# ---------------------------------------------------------------------------
# Module loading with Django and the openai SDK stubbed out.
# ---------------------------------------------------------------------------
class _Settings:
    """Minimal stand-in for django.conf.settings.

    Deliberately does NOT define OPENAI_CHATGPT_MODEL or LLM_MAX_OUTPUT_TOKENS,
    so the tests below exercise the in-code getattr fallbacks rather than the
    settings.py defaults. Those fallbacks are what a process with an incomplete
    settings module actually gets, and a stale one there 404s or truncates.
    """

    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    OPENROUTER_SITE_URL = "https://app.promptmaxx.co"
    OPENROUTER_SITE_TITLE = "PromptMaxx"
    OPENROUTER_API_KEY = "sk-or-system-key"
    OPENROUTER_INTERNAL_MODEL = "openai/gpt-5-mini"
    OPENAI_API_KEY = "sk-proj-stale-openai-key"
    # Force the chat.completions branch so the test does not depend on the
    # /responses surface, which is covered by the live probe documented above.
    OPENAI_CHATGPT_WEB_SEARCH = False


class _FakeOpenAI:
    """Records the base_url/key the factory builds the client with."""

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs


class _RecordingClient:
    """An openai client that records the model of the call it receives."""

    def __init__(self, text="ChatGPT answer mentioning example.com"):
        self.calls = []
        outer = self

        class _Completions:
            def create(self, **kwargs):
                outer.calls.append(kwargs)
                message = types.SimpleNamespace(content=text)
                return types.SimpleNamespace(
                    choices=[types.SimpleNamespace(message=message)]
                )

        self.chat = types.SimpleNamespace(completions=_Completions())


def _install_stubs():
    conf = types.ModuleType('django.conf')
    conf.settings = _Settings()
    cache_mod = types.ModuleType('django.core.cache')
    cache_mod.cache = types.SimpleNamespace(get=lambda *a, **k: None, set=lambda *a, **k: None)
    openai_mod = types.ModuleType('openai')
    openai_mod.OpenAI = _FakeOpenAI
    sys.modules.update({
        'django': types.ModuleType('django'),
        'django.conf': conf,
        'django.core': types.ModuleType('django.core'),
        'django.core.cache': cache_mod,
        'openai': openai_mod,
        'textblob': types.ModuleType('textblob'),
    })


def _load(module_name, filename):
    """Load one engine module by path, under a synthetic package so the
    relative `from .api_key_service import ...` in client_factory resolves."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_install_stubs()
_PKG = 'openai_or_test_pkg'
package = types.ModuleType(_PKG)
package.__path__ = []
sys.modules[_PKG] = package
AKS = _load(f'{_PKG}.api_key_service', os.path.join('services', 'api_key_service.py'))
CF = _load(f'{_PKG}.client_factory', os.path.join('services', 'client_factory.py'))
AH = _load('openai_or_test_analytics_helpers', 'analytics_helpers.py')


# ---------------------------------------------------------------------------
# 1. Credential routing
# ---------------------------------------------------------------------------
def test_openai_authenticates_with_the_openrouter_key():
    print("  'openai' resolves to the OpenRouter credential, not the vendor one")
    assert AKS.credential_provider('openai') == 'openrouter', (
        "ChatGPT must authenticate with the OpenRouter key; resolving to "
        "'openai' sends an OpenAI key to OpenRouter, which cannot parse it and "
        "answers 401 'Missing Authentication header'."
    )
    # The providers routed earlier must not have been disturbed.
    assert AKS.credential_provider('anthropic') == 'openrouter'
    assert AKS.credential_provider('perplexity') == 'openrouter'
    # Everything else still uses its own vendor key.
    for provider in ('gemini', 'xai', 'deepseek'):
        assert AKS.credential_provider(provider) == provider, provider


def test_the_env_fallback_returns_the_openrouter_key_for_openai():
    print("  the .env fallback hands back OPENROUTER_API_KEY, not OPENAI_API_KEY")
    key = AKS.get_api_key(None, AKS.credential_provider('openai'))
    assert key == 'sk-or-system-key', f"got {key!r}"


# ---------------------------------------------------------------------------
# 2. Client construction
# ---------------------------------------------------------------------------
def test_client_is_pointed_at_openrouter_not_openai():
    print("  the built client targets openrouter.ai, never api.openai.com")
    client = CF._build_client('openai', 'sk-or-system-key')
    base_url = client.init_kwargs['base_url']
    assert base_url == 'https://openrouter.ai/api/v1', base_url
    assert 'api.openai.com' not in base_url, base_url
    assert client.init_kwargs['api_key'] == 'sk-or-system-key'


def test_client_sends_openrouter_attribution_headers():
    print("  attribution headers match the Claude/Perplexity transport's")
    client = CF._build_client('openai', 'sk-or-system-key')
    assert client.init_kwargs['default_headers'] == {
        'HTTP-Referer': 'https://app.promptmaxx.co',
        'X-Title': 'PromptMaxx',
    }, client.init_kwargs['default_headers']


# ---------------------------------------------------------------------------
# 3. Model slug — the silent 404 this switch could have caused
# ---------------------------------------------------------------------------
def test_tracked_call_uses_an_openrouter_prefixed_slug():
    print("  the tracked ChatGPT call sends a prefixed slug, never a bare one")
    client = _RecordingClient()
    # _Settings intentionally omits OPENAI_CHATGPT_MODEL, so this asserts the
    # in-code fallback is prefixed too — a bare slug 404s on OpenRouter.
    AH.process_prompt_with_chatgpt("best crm for startups", "example.com", client)
    assert client.calls, "the chat.completions path was never reached"
    model = client.calls[-1]['model']
    assert model.startswith('openai/'), (
        f"got {model!r}; a bare OpenAI model id is not a valid OpenRouter slug "
        f"and 404s, silently zeroing ChatGPT tracking."
    )


def test_one_model_serves_internal_and_tracked_calls_alike():
    print("  the measured call runs the same model as internal work")
    client = _RecordingClient()
    AH.process_prompt_with_chatgpt("best crm for startups", "example.com", client)
    tracked = client.calls[-1]['model']
    assert tracked == _Settings.OPENROUTER_INTERNAL_MODEL, (
        f"tracked call is on {tracked!r} but internal work is on "
        f"{_Settings.OPENROUTER_INTERNAL_MODEL!r}; the platform is meant to run "
        f"ONE model everywhere. Split them from .env, not by drifting defaults."
    )


# ---------------------------------------------------------------------------
# 4. Reasoning-token headroom — the truncation this model change could cause
# ---------------------------------------------------------------------------
def test_token_ceiling_leaves_room_for_hidden_reasoning():
    print("  the ceiling covers gpt-5-mini's reasoning tokens, not just the answer")
    client = _RecordingClient()
    AH.process_prompt_with_chatgpt("best crm for startups", "example.com", client)
    max_tokens = client.calls[-1]['max_tokens']
    # Measured on prod against OpenRouter 2026-07-27 with the REAL analytics
    # prompt: gpt-5-mini truncated (finish_reason='length') at both 3000 and
    # 5000, burning 1792 and 1984 reasoning tokens respectively, and completed
    # only at 8000 (1216 reasoning, 4228 total). Below ~6000 every answer
    # truncates and drops the trailing citation list the Citations page counts.
    assert max_tokens >= 6000, (
        f"ceiling {max_tokens} is too tight for a reasoning model — hidden "
        f"reasoning eats it before any text is emitted, truncating the answer "
        f"and silently deflating citation counts."
    )


def test_empty_reasoning_response_fails_loudly():
    print("  content=None raises rather than recording a false 'no mention'")
    client = _RecordingClient(text=None)
    try:
        AH.process_prompt_with_chatgpt("best crm for startups", "example.com", client)
    except Exception:
        return  # correct: the caller marks the prompt FAIL and can retry
    raise AssertionError(
        "an empty model response was recorded as a genuine zero-mention result; "
        "that deflates the score instead of surfacing the failure."
    )


if __name__ == '__main__':
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            print(f"{name}:")
            try:
                fn()
            except AssertionError as exc:
                failures += 1
                print(f"  FAIL: {exc}")
    print("\nFAILED" if failures else "\nAll ChatGPT->OpenRouter tests passed.")
    sys.exit(1 if failures else 0)
