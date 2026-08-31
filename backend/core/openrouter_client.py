"""
backend/core/openrouter_client.py

Anthropic-shaped adapter over OpenRouter's OpenAI-compatible Chat Completions API.

Near-copy of engine/core/services/openrouter_client.py. The backend and engine are
separate Django projects with separate virtualenvs and no shared import path, so
the adapter is duplicated the same way api_key_service already duplicates BYOK
decryption across the two trees.

The two files are NOT identical and never have been: this copy carries an extra
``get_internal_client`` that the engine provides from its own client_factory
instead. What MUST stay in sync is the request/response translation — everything
in ``_MessagesAPI`` and its helpers. A fix applied to one copy and not the other
means a call site in the other tree keeps the bug.

``tests/standalone/engine/core/test_openrouter_client.py`` loads BOTH files and asserts the
translation matches, so that divergence fails a test rather than reaching
production. Change both files together and run it.

OpenRouter exposes only ``POST /api/v1/chat/completions`` — there is no Anthropic
``/v1/messages`` endpoint. Every Claude call site in this codebase was written
against the Anthropic SDK (``client.messages.create(model=..., system=...)``
returning ``.content`` blocks and ``.usage.input_tokens``). Rather than rewrite
those call sites across two Django trees, this adapter presents the Anthropic
Messages surface and translates to OpenRouter underneath.

Translation performed here:
    system="..."                      -> a leading {"role": "system"} message
    tools=[{... web_search ...}]      -> OpenRouter's ``web`` plugin (live browsing)
    tools=[<function tool>]           -> passed through unchanged (Sonnet 5 supports tools)
    choices[0].message.content        -> response.content[0].text
    usage.prompt_tokens               -> response.usage.input_tokens
    usage.completion_tokens           -> response.usage.output_tokens

Anthropic's native ``web_search_20250305`` server-side tool does not exist on
OpenRouter. When a caller asks for it we enable OpenRouter's ``web`` plugin so
Claude still browses before answering. That is a *different* search backend, so
grounded answers will not be byte-identical to the previous Anthropic path.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# OpenRouter bills the web plugin per query, so keep the ceiling explicit rather
# than relying on the plugin default.
DEFAULT_WEB_MAX_RESULTS = 5


@dataclass(frozen=True)
class TextBlock:
    """Mirrors an Anthropic ``content`` block so ``block.type``/``block.text`` still work."""

    text: str
    type: str = "text"


@dataclass(frozen=True)
class Usage:
    """Mirrors ``response.usage`` from the Anthropic SDK."""

    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class Message:
    """Mirrors the Anthropic ``Message`` object returned by ``messages.create``."""

    content: Tuple[TextBlock, ...]
    usage: Usage
    model: str
    stop_reason: Optional[str] = None
    citations: Tuple[str, ...] = ()


def _flatten_content(content: Any) -> str:
    """Collapse Anthropic block-style content into the plain string OpenRouter expects."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, Sequence):
        parts: List[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", "") or "")
            else:
                text = getattr(block, "text", None)
                if text:
                    parts.append(text)
        return "\n".join(p for p in parts if p)
    return str(content)


def _normalise_messages(messages: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Convert Anthropic-style messages to OpenAI chat messages."""
    return [
        {"role": m.get("role", "user"), "content": _flatten_content(m.get("content"))}
        for m in (messages or [])
    ]


def _is_web_search_tool(tool: Any) -> bool:
    """True when the caller asked for Anthropic's server-side web search tool."""
    if not isinstance(tool, dict):
        return False
    return "web_search" in f"{tool.get('type', '')}{tool.get('name', '')}"


def _translate_tools(tools: Optional[Sequence[Any]]) -> Tuple[List[Any], List[Dict[str, Any]]]:
    """Split requested tools into (passthrough tools, OpenRouter plugins)."""
    if not tools:
        return [], []

    passthrough: List[Any] = []
    plugins: List[Dict[str, Any]] = []
    for tool in tools:
        if _is_web_search_tool(tool):
            max_results = tool.get("max_uses") or DEFAULT_WEB_MAX_RESULTS
            plugins.append({"id": "web", "max_results": int(max_results)})
        else:
            passthrough.append(tool)
    return passthrough, plugins


def _extract_citations(message: Any) -> Tuple[str, ...]:
    """Pull URL citations out of an OpenRouter web-plugin response, if present."""
    urls: List[str] = []
    for annotation in getattr(message, "annotations", None) or []:
        try:
            citation = annotation.get("url_citation") if isinstance(annotation, dict) else None
            if citation and citation.get("url"):
                urls.append(citation["url"])
        except Exception:  # noqa: BLE001 - annotations are best-effort metadata
            continue
    return tuple(urls)


def _to_message(response: Any, model: str) -> Message:
    """Convert an OpenAI-shaped completion into an Anthropic-shaped Message."""
    choice = (getattr(response, "choices", None) or [None])[0]
    chat_message = getattr(choice, "message", None)
    text = getattr(chat_message, "content", "") or ""

    usage = getattr(response, "usage", None)
    return Message(
        content=(TextBlock(text=text),),
        usage=Usage(
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        ),
        model=getattr(response, "model", model),
        stop_reason=getattr(choice, "finish_reason", None),
        citations=_extract_citations(chat_message),
    )


class _MessagesAPI:
    """Implements the ``client.messages.create(...)`` surface of the Anthropic SDK."""

    def __init__(self, openai_client: Any, default_model: Optional[str]) -> None:
        self._client = openai_client
        self._default_model = default_model

    def create(
        self,
        *,
        messages: Sequence[Dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        system: Any = None,
        temperature: Optional[float] = None,
        tools: Optional[Sequence[Any]] = None,
        reasoning: Optional[Dict[str, Any]] = None,
        **unsupported: Any,
    ) -> Message:
        chat_messages: List[Dict[str, str]] = []
        system_text = _flatten_content(system)
        if system_text:
            chat_messages.append({"role": "system", "content": system_text})
        chat_messages.extend(_normalise_messages(messages))

        passthrough_tools, plugins = _translate_tools(tools)

        resolved_model = model or self._default_model
        if not resolved_model:
            raise ValueError("OpenRouterAnthropicClient: no model configured for this call")

        kwargs: Dict[str, Any] = {"model": resolved_model, "messages": chat_messages}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            kwargs["temperature"] = temperature
        if passthrough_tools:
            kwargs["tools"] = passthrough_tools

        # `plugins` and `reasoning` share one extra_body, so build it up rather
        # than assigning — the previous `extra_body = {"plugins": ...}` form would
        # have silently dropped whichever of the two was set second. Omitted
        # entirely when neither is used, so callers that pass no reasoning send a
        # byte-identical request to before this parameter existed.
        extra_body: Dict[str, Any] = {}
        if plugins:
            extra_body["plugins"] = plugins
        if reasoning is not None:
            # OpenRouter-only argument: the OpenAI API rejects `reasoning` with
            # "Unrecognized request argument". When OPENROUTER_BASE_URL is
            # pointed directly at api.openai.com (local dev with a bare OpenAI
            # key), drop it so every caller keeps working on both transports.
            from django.conf import settings as _s
            if 'openrouter' in (getattr(_s, 'OPENROUTER_BASE_URL', '') or ''):
                extra_body["reasoning"] = reasoning
        if extra_body:
            kwargs["extra_body"] = extra_body

        if unsupported:
            # Anthropic-only arguments (e.g. top_k, metadata) have no OpenRouter
            # equivalent. Drop them loudly rather than passing them through and
            # taking a 400 from the API.
            logger.debug(
                "OpenRouterAnthropicClient: dropping unsupported argument(s) %s",
                ", ".join(sorted(unsupported)),
            )

        response = self._client.chat.completions.create(**kwargs)
        return _to_message(response, resolved_model)


def resolve_openrouter_key(org=None) -> Optional[str]:
    """The OpenRouter key to use: this organisation's own, else the system key.

    A customer only ever sees the frontend — they cannot edit ``.env`` — so the
    key they paste into Settings > Organization > API Keys has to be the one
    that actually authenticates their work, and their usage has to bill to their
    account rather than the operator's.

    Resolution order matches ``engine.core.services.api_key_service.get_api_key``
    and the proven Gemini path in ``domains.views.get_google_genai_client``:

        1. Organisation.openrouter_api_key   (BYOK, encrypted in the database)
        2. settings.OPENROUTER_API_KEY       (system key — development, and a
                                              fallback for background jobs)

    ``org`` may be passed explicitly. When it is not, the current request's
    organisation is resolved from thread-local state, which is populated by
    ``ThreadLocalRequestMiddleware``. Outside a request — Celery tasks,
    management commands — that returns None and the system key is used, which is
    the correct behaviour for work that belongs to no particular user.

    Every failure here degrades to the system key rather than raising: a broken
    cache or an unreadable ciphertext must not take LLM features offline.
    """
    from django.conf import settings

    if org is None:
        try:
            from llm_monitor.middleware import get_current_org_id
            from engine.core.services.api_key_service import get_org_settings

            org_id = get_current_org_id()
            if org_id:
                org = get_org_settings(org_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning('Could not resolve organisation for BYOK key: %s', exc)
            org = None

    if org is not None:
        try:
            from engine.core.services.api_key_service import get_api_key
            key = get_api_key(org, 'openrouter')
            if key:
                return key
        except Exception as exc:  # noqa: BLE001
            logger.warning('BYOK OpenRouter lookup failed, using system key: %s', exc)

    return getattr(settings, 'OPENROUTER_API_KEY', None)


def get_internal_client(timeout: int = 60, org=None) -> Any:
    """Plain OpenAI-compatible client pointed at OpenRouter, for INTERNAL work.

    Used by the backend's non-measured LLM calls (chat, domain helpers, insight
    generation, misinformation comparison). The AI Mention Check builds its own
    OpenRouter client instead of using this one — same transport, but it keeps
    the flagship ``OPENAI_CHATGPT_MODEL`` so it still measures what a real
    ChatGPT user is told, rather than the cheap internal slug below.

    Authenticates with the CALLER'S organisation key when there is one, so a
    customer who pastes their key in Settings pays for their own usage. Pass
    ``org`` explicitly from background work, where there is no request to infer
    it from.

    Pair with ``settings.OPENROUTER_INTERNAL_MODEL`` for the model slug.
    """
    from django.conf import settings
    from openai import OpenAI

    api_key = resolve_openrouter_key(org)
    if not api_key:
        raise ValueError(
            'No OpenRouter API key available. Add one in Settings > '
            'Organization > API Keys, or set OPENROUTER_API_KEY.'
        )
    return OpenAI(
        api_key=api_key,
        base_url=getattr(settings, 'OPENROUTER_BASE_URL', OPENROUTER_BASE_URL),
        timeout=timeout,
    )


class OpenRouterAnthropicClient:
    """Drop-in replacement for ``anthropic.Anthropic`` backed by OpenRouter.

    Only the ``messages.create`` surface used by this codebase is implemented.
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        site_url: Optional[str] = None,
        site_title: Optional[str] = None,
    ) -> None:
        from openai import OpenAI

        headers: Dict[str, str] = {}
        if site_url:
            headers["HTTP-Referer"] = site_url
        if site_title:
            headers["X-Title"] = site_title

        self.model = model
        self._openai = OpenAI(
            api_key=api_key,
            base_url=base_url or OPENROUTER_BASE_URL,
            timeout=timeout,
            default_headers=headers or None,
        )
        self.messages = _MessagesAPI(self._openai, model)
