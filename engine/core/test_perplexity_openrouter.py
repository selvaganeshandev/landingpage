"""
Test script for the Perplexity → OpenRouter transport switch.

The direct api.perplexity.ai key ran out of credit, so every Perplexity call
died on a 401 insufficient_quota and that platform's tracking silently went to
zero. Perplexity now rides OpenRouter alongside Claude, on one shared balance.

Three things have to hold for that switch to be invisible downstream:

  1. The credential for 'perplexity' resolves to the OpenRouter key, not the
     (now dead) Perplexity one.
  2. The client is pointed at OpenRouter, never at api.perplexity.ai — a client
     still aimed at the old host would fail exactly the way it did before.
  3. Citations survive. This is the non-obvious one: verified live against
     openrouter.ai on 2026-07-27, `perplexity/sonar` returns its sources ONLY in
     `message.annotations` and leaves the top-level `citations` list EMPTY,
     which is the reverse of the direct Perplexity API. Reading just `citations`
     — as the code did before — would have zeroed the Citations page for
     Perplexity while every response still looked fine.

Everything is stubbed (Django, the openai SDK). No network, no database, no
API key required.

Run:  python core/test_perplexity_openrouter.py     (from the engine/ directory)
"""
import importlib.util
import os
import sys
import types

# ---------------------------------------------------------------------------
# Fixtures — the real response shapes, captured from the live providers.
# ---------------------------------------------------------------------------

# What OpenRouter actually returned for perplexity/sonar on 2026-07-27, as the
# openai SDK (>=2.31) parses it: typed Annotation objects, no top-level citations.
SONAR_ANNOTATION_URLS = [
    "https://www.wincalendar.com/Calendar/Date/July-27-2026",
    "https://www.timeanddate.com/calendar/monthly.html",
]

# The direct Perplexity API's older shape, kept working so a response carrying
# either form still yields sources.
LEGACY_CITATION_URLS = ["https://example.com/a", "https://example.com/b"]


def _sdk_annotation(url):
    """An openai.types.chat.Annotation, which is an OBJECT and not a dict."""
    return types.SimpleNamespace(
        type="url_citation",
        url_citation=types.SimpleNamespace(url=url, title="t", start_index=0, end_index=1),
    )


def _response(citations=None, annotations=None):
    message = types.SimpleNamespace(content="answer", annotations=annotations)
    response = types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])
    if citations is not None:
        response.citations = citations
    return response


# ---------------------------------------------------------------------------
# Module loading with Django and the openai SDK stubbed out.
# ---------------------------------------------------------------------------
class _Settings:
    """Minimal stand-in for django.conf.settings."""

    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    OPENROUTER_SITE_URL = "https://app.promptmaxx.co"
    OPENROUTER_SITE_TITLE = "PromptMaxx"
    OPENROUTER_API_KEY = "sk-or-system-key"
    PERPLEXITY_API_KEY = "pplx-dead-key"


class _FakeOpenAI:
    """Records the base_url/key the factory builds the client with."""

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs


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
_PKG = 'pplx_or_test_pkg'
package = types.ModuleType(_PKG)
package.__path__ = []
sys.modules[_PKG] = package
AKS = _load(f'{_PKG}.api_key_service', os.path.join('services', 'api_key_service.py'))
CF = _load(f'{_PKG}.client_factory', os.path.join('services', 'client_factory.py'))
AH = _load('pplx_or_test_analytics_helpers', 'analytics_helpers.py')


# ---------------------------------------------------------------------------
# 1. Credential routing
# ---------------------------------------------------------------------------
def test_perplexity_authenticates_with_the_openrouter_key():
    print("  'perplexity' resolves to the OpenRouter credential, not the dead one")
    assert AKS.credential_provider('perplexity') == 'openrouter', (
        "Perplexity must authenticate with the OpenRouter key; resolving to "
        "'perplexity' sends the dead api.perplexity.ai credential and 401s."
    )
    # Claude's existing routing must not have been disturbed.
    assert AKS.credential_provider('anthropic') == 'openrouter'
    # Everything else still uses its own vendor key.
    for provider in ('openai', 'gemini', 'xai', 'deepseek'):
        assert AKS.credential_provider(provider) == provider, provider


def test_the_env_fallback_returns_the_openrouter_key_for_perplexity():
    print("  the .env fallback hands back OPENROUTER_API_KEY")
    key = AKS.get_api_key(None, AKS.credential_provider('perplexity'))
    assert key == 'sk-or-system-key', f"got {key!r}"


# ---------------------------------------------------------------------------
# 2. Client construction
# ---------------------------------------------------------------------------
def test_client_is_pointed_at_openrouter_not_perplexity():
    print("  the built client targets openrouter.ai, never api.perplexity.ai")
    client = CF._build_client('perplexity', 'sk-or-system-key')
    base_url = client.init_kwargs['base_url']
    assert 'api.perplexity.ai' not in base_url, (
        f"client still points at the dead host: {base_url}"
    )
    assert base_url == 'https://openrouter.ai/api/v1', base_url
    assert client.init_kwargs['api_key'] == 'sk-or-system-key'


def test_client_sends_openrouter_attribution_headers():
    print("  attribution headers match the Claude transport's")
    client = CF._build_client('perplexity', 'sk-or-system-key')
    headers = client.init_kwargs['default_headers']
    assert headers == {
        'HTTP-Referer': 'https://app.promptmaxx.co',
        'X-Title': 'PromptMaxx',
    }, headers


def test_headers_are_omitted_entirely_when_unconfigured():
    print("  no attribution configured, no empty header mapping is sent")
    saved = (_Settings.OPENROUTER_SITE_URL, _Settings.OPENROUTER_SITE_TITLE)
    _Settings.OPENROUTER_SITE_URL = None
    _Settings.OPENROUTER_SITE_TITLE = None
    try:
        assert CF._openrouter_headers() is None
    finally:
        _Settings.OPENROUTER_SITE_URL, _Settings.OPENROUTER_SITE_TITLE = saved


# ---------------------------------------------------------------------------
# 3. Citations — the regression this switch could have caused silently
# ---------------------------------------------------------------------------
def test_citations_are_read_from_openrouter_annotations():
    print("  sources are extracted from annotations (OpenRouter's only channel)")
    response = _response(
        citations=[],  # OpenRouter leaves this EMPTY for perplexity/sonar
        annotations=[_sdk_annotation(u) for u in SONAR_ANNOTATION_URLS],
    )
    assert AH._extract_sonar_citations(response) == SONAR_ANNOTATION_URLS


def test_legacy_top_level_citations_still_work():
    print("  the direct Perplexity API's top-level citations still parse")
    assert AH._extract_sonar_citations(
        _response(citations=LEGACY_CITATION_URLS)
    ) == LEGACY_CITATION_URLS
    # Newer dict form: {"url": ...}
    assert AH._extract_sonar_citations(
        _response(citations=[{"url": u} for u in LEGACY_CITATION_URLS])
    ) == LEGACY_CITATION_URLS


def test_raw_dict_annotations_parse_too():
    print("  annotations delivered as plain dicts parse identically")
    response = _response(annotations=[
        {"type": "url_citation", "url_citation": {"url": u}} for u in SONAR_ANNOTATION_URLS
    ])
    assert AH._extract_sonar_citations(response) == SONAR_ANNOTATION_URLS


def test_duplicates_are_dropped_and_order_preserved():
    print("  a URL cited in both channels is counted once")
    first, second = SONAR_ANNOTATION_URLS
    response = _response(
        citations=[first],
        annotations=[_sdk_annotation(first), _sdk_annotation(second)],
    )
    assert AH._extract_sonar_citations(response) == [first, second]


def test_a_response_with_no_sources_yields_no_citations():
    print("  an unsourced response yields [] rather than raising")
    assert AH._extract_sonar_citations(_response()) == []
    assert AH._extract_sonar_citations(_response(citations=None, annotations=None)) == []
    assert AH._extract_sonar_citations(types.SimpleNamespace()) == []


TESTS = [
    test_perplexity_authenticates_with_the_openrouter_key,
    test_the_env_fallback_returns_the_openrouter_key_for_perplexity,
    test_client_is_pointed_at_openrouter_not_perplexity,
    test_client_sends_openrouter_attribution_headers,
    test_headers_are_omitted_entirely_when_unconfigured,
    test_citations_are_read_from_openrouter_annotations,
    test_legacy_top_level_citations_still_work,
    test_raw_dict_annotations_parse_too,
    test_duplicates_are_dropped_and_order_preserved,
    test_a_response_with_no_sources_yields_no_citations,
]


def main():
    print("Perplexity -> OpenRouter transport")
    failures = 0
    for test in TESTS:
        try:
            test()
        except AssertionError as exc:
            failures += 1
            print(f"    FAIL {test.__name__}: {exc}")
    print(f"\n{len(TESTS) - failures}/{len(TESTS)} passed")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
