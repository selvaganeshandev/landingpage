"""
Tests for the Anthropic-shaped OpenRouter adapter.

Every Claude call site in both trees still speaks the Anthropic Messages API, so
the only thing standing between those call sites and OpenRouter is the
translation in openrouter_client.py. The things that must hold:

  - `system=` becomes a leading system message (dropping it silently would strip
    the country/date grounding instructions from every tracked answer)
  - Anthropic's web_search tool becomes OpenRouter's `web` plugin and is NOT
    forwarded as a tool (forwarding it is a 400 from the API)
  - the response maps back to `.content[0].text` and `.usage.input_tokens`,
    which ~30 content-generation call sites index directly
  - Anthropic-only kwargs are dropped rather than passed through as a 400

The module imports openai lazily inside __init__, so this stubs the SDK and
needs no Django, network, or database.

Run:  python core/test_openrouter_client.py
"""
import importlib.util
import os
import sys
import types

_CAPTURED = []


class _FakeUsage:
    prompt_tokens = 11
    completion_tokens = 22


class _FakeMessage:
    content = "hello from openrouter"
    annotations = [{"url_citation": {"url": "https://example.com/a"}}]


class _FakeChoice:
    message = _FakeMessage()
    finish_reason = "stop"


class _FakeResponse:
    choices = [_FakeChoice()]
    usage = _FakeUsage()
    model = "anthropic/claude-sonnet-5"


class _FakeCompletions:
    def create(self, **kwargs):
        _CAPTURED.append(kwargs)
        return _FakeResponse()


class _FakeChat:
    completions = _FakeCompletions()


class _FakeOpenAI:
    """Stand-in for openai.OpenAI that records how it was constructed."""

    def __init__(self, **kwargs):
        _CAPTURED.append({"__init__": kwargs})
        self.chat = _FakeChat()


def _load_adapter():
    """Import openrouter_client with the openai SDK stubbed out."""
    openai_stub = types.ModuleType('openai')
    openai_stub.OpenAI = _FakeOpenAI
    sys.modules['openai'] = openai_stub

    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'services', 'openrouter_client.py'
    )
    spec = importlib.util.spec_from_file_location('openrouter_client_undertest', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules['openrouter_client_undertest'] = module
    spec.loader.exec_module(module)
    return module


OR = _load_adapter()

_PASS, _FAIL = [], []


def check(name, condition, detail=''):
    (_PASS if condition else _FAIL).append(name)
    print(f"  {'PASS' if condition else 'FAIL'}  {name}{('  -> ' + str(detail)) if detail and not condition else ''}")


def _client(**kwargs):
    _CAPTURED.clear()
    return OR.OpenRouterAnthropicClient(api_key='sk-or-test', **kwargs)


def _last_request():
    """The kwargs of the most recent chat.completions.create call."""
    return [c for c in _CAPTURED if '__init__' not in c][-1]


print("\nopenrouter_client — request translation")

client = _client(model='anthropic/claude-sonnet-5')
client.messages.create(
    max_tokens=1500,
    temperature=0.7,
    system="Answer in the context of India.",
    messages=[{"role": "user", "content": "who sells crm software"}],
)
req = _last_request()
check("system prompt becomes a leading system message",
      req['messages'][0] == {"role": "system", "content": "Answer in the context of India."},
      req['messages'])
check("user message follows the system message",
      req['messages'][1] == {"role": "user", "content": "who sells crm software"},
      req['messages'])
check("model falls back to the client default",
      req['model'] == 'anthropic/claude-sonnet-5', req['model'])
check("max_tokens forwarded", req.get('max_tokens') == 1500, req)
check("temperature forwarded", req.get('temperature') == 0.7, req)
check("no plugins when no tools requested", 'extra_body' not in req, req)

client = _client(model='anthropic/claude-sonnet-5')
client.messages.create(
    messages=[{"role": "user", "content": "ping"}],
    tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
)
req = _last_request()
check("web_search tool becomes the OpenRouter web plugin",
      req.get('extra_body') == {"plugins": [{"id": "web", "max_results": 5}]}, req)
check("web_search tool is NOT forwarded as a tool", 'tools' not in req, req)

client = _client(model='anthropic/claude-sonnet-5')
client.messages.create(
    messages=[{"role": "user", "content": "ping"}],
    tools=[{"type": "function", "function": {"name": "lookup"}}],
)
req = _last_request()
check("function tools pass through unchanged",
      req.get('tools') == [{"type": "function", "function": {"name": "lookup"}}], req)
check("function tools produce no plugin", 'extra_body' not in req, req)

client = _client(model='anthropic/claude-sonnet-5')
client.messages.create(
    messages=[{"role": "user", "content": [{"type": "text", "text": "block one"},
                                           {"type": "text", "text": "block two"}]}],
)
req = _last_request()
check("block-style content is flattened to a string",
      req['messages'][0]['content'] == "block one\nblock two", req['messages'])

client = _client(model='anthropic/claude-sonnet-5')
client.messages.create(
    messages=[{"role": "user", "content": "ping"}],
    top_k=5,
    metadata={"user_id": "42"},
)
req = _last_request()
check("Anthropic-only kwargs are dropped, not forwarded",
      'top_k' not in req and 'metadata' not in req, req)

print("\nopenrouter_client — response translation")

client = _client(model='anthropic/claude-sonnet-5')
resp = client.messages.create(messages=[{"role": "user", "content": "ping"}])
check("response.content[0].text carries the answer",
      resp.content[0].text == "hello from openrouter", resp.content)
check("response.content[0].type is 'text'", resp.content[0].type == "text", resp.content)
check("usage.input_tokens maps from prompt_tokens", resp.usage.input_tokens == 11, resp.usage)
check("usage.output_tokens maps from completion_tokens", resp.usage.output_tokens == 22, resp.usage)
check("stop_reason maps from finish_reason", resp.stop_reason == "stop", resp.stop_reason)
check("web plugin citations are captured",
      resp.citations == ("https://example.com/a",), resp.citations)

print("\nopenrouter_client — configuration")

_CAPTURED.clear()
OR.OpenRouterAnthropicClient(api_key='sk-or-test', model='anthropic/claude-sonnet-5',
                            site_url='https://app.promptmaxx.co', site_title='PromptMaxx')
init = [c for c in _CAPTURED if '__init__' in c][0]['__init__']
check("defaults to the OpenRouter base URL",
      init['base_url'] == 'https://openrouter.ai/api/v1', init)
check("attribution headers are sent when configured",
      init['default_headers'] == {"HTTP-Referer": "https://app.promptmaxx.co",
                                  "X-Title": "PromptMaxx"}, init)

_CAPTURED.clear()
OR.OpenRouterAnthropicClient(api_key='sk-or-test', model='anthropic/claude-sonnet-5')
init = [c for c in _CAPTURED if '__init__' in c][0]['__init__']
check("no header dict when attribution is unconfigured",
      init['default_headers'] is None, init)

client = _client()
try:
    client.messages.create(messages=[{"role": "user", "content": "ping"}])
    check("a call with no model anywhere raises", False, "no exception raised")
except ValueError:
    check("a call with no model anywhere raises", True)

print(f"\n{len(_PASS)} passed, {len(_FAIL)} failed")
if _FAIL:
    for name in _FAIL:
        print(f"  FAILED: {name}")
sys.exit(1 if _FAIL else 0)
