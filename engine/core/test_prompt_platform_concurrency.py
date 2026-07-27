"""
Tests for the concurrent platform runner in PromptAnalyticsProcessor.

Prompt tracking used to run every platform for a prompt strictly one after the
other, so a prompt cost the SUM of its providers' latencies (~30s for three
~10s calls). _run_platforms fans those independent calls out instead, and these
tests pin the properties that made that safe to do:

  * results are complete and correctly keyed regardless of ordering,
  * one provider failing still isolates to that provider,
  * clients are resolved on the CALLING thread, never inside the pool (pool
    threads must not touch Redis or the ORM),
  * MAX_CONCURRENT_PROMPT_PLATFORMS=1 restores the old serial behaviour,
  * the work actually overlaps.

Deliberately DB-free (SimpleTestCase, databases = []): _run_platforms takes the
prompt text and group as arguments and touches no model, so these run without a
database — which matters here because this project's dev environment points at
the production database.
"""
import threading
import time
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .prompt_analytics_processor import PromptAnalyticsProcessor


class _StubDomain:
    country = "United States"


class _StubGroup:
    domain = _StubDomain()


def _make_processor():
    """A processor with the platform handlers stubbed out.

    __init__ calls _load_helpers, which imports the real analytics_helpers; the
    handlers are replaced afterwards so no LLM SDK is ever constructed.
    """
    return PromptAnalyticsProcessor(max_concurrent_prompts=10)


class RunPlatformsTests(SimpleTestCase):
    databases = []

    def setUp(self):
        self.processor = _make_processor()

        # Every platform "succeeds" with an identifiable payload.
        def _handler_for(platform):
            def _handler(prompt_text, user_domain, client, group):
                return {'platform_echo': platform, 'client': client, 'fallback': False}
            return _handler

        self.processor._process_prompt_with_chatgpt = _handler_for('chatgpt')
        self.processor._process_prompt_with_gemini = _handler_for('gemini')
        self.processor._process_prompt_with_perplexity = _handler_for('perplexity')
        self.processor._process_prompt_with_claude = _handler_for('claude')
        self.processor._process_prompt_with_grok = _handler_for('grok')
        self.processor._process_prompt_with_deepseek = _handler_for('deepseek')

    def _run(self, platforms, **kwargs):
        return self.processor._run_platforms(
            platforms=platforms,
            prompt_text="best crm software",
            user_domain="example.com",
            group=_StubGroup(),
            org_id=7,
            label="test",
            **kwargs
        )

    @override_settings(MAX_CONCURRENT_PROMPT_PLATFORMS=3)
    def test_every_platform_returns_its_own_result(self):
        """Results are keyed by platform and never cross-assigned."""
        with patch.object(self.processor, '_resolve_client', return_value='CLIENT'):
            results = self._run(['chatgpt', 'perplexity', 'claude'])

        self.assertEqual(set(results), {'chatgpt', 'perplexity', 'claude'})
        for platform in ('chatgpt', 'perplexity', 'claude'):
            self.assertEqual(results[platform]['platform_echo'], platform)

    @override_settings(MAX_CONCURRENT_PROMPT_PLATFORMS=3)
    def test_platform_calls_actually_overlap(self):
        """Three 0.3s calls must finish in well under the 0.9s serial cost."""
        def _slow(prompt_text, user_domain, client, group):
            time.sleep(0.3)
            return {'fallback': False}

        self.processor._process_prompt_with_chatgpt = _slow
        self.processor._process_prompt_with_perplexity = _slow
        self.processor._process_prompt_with_claude = _slow

        with patch.object(self.processor, '_resolve_client', return_value='CLIENT'):
            started = time.monotonic()
            results = self._run(['chatgpt', 'perplexity', 'claude'])
            elapsed = time.monotonic() - started

        self.assertEqual(len(results), 3)
        self.assertLess(
            elapsed, 0.7,
            f"platform calls did not overlap: {elapsed:.2f}s for 3x0.3s (serial would be ~0.9s)"
        )

    @override_settings(MAX_CONCURRENT_PROMPT_PLATFORMS=3)
    def test_one_failing_platform_does_not_affect_the_others(self):
        """A raising provider falls back alone; real results are preserved."""
        def _boom(prompt_text, user_domain, client, group):
            raise RuntimeError("provider exploded")

        self.processor._process_prompt_with_perplexity = _boom

        with patch.object(self.processor, '_resolve_client', return_value='CLIENT'):
            results = self._run(['chatgpt', 'perplexity', 'claude'])

        self.assertEqual(set(results), {'chatgpt', 'perplexity', 'claude'})
        self.assertTrue(results['perplexity'].get('fallback'))
        # The healthy providers kept their genuine answers.
        self.assertEqual(results['chatgpt']['platform_echo'], 'chatgpt')
        self.assertEqual(results['claude']['platform_echo'], 'claude')

    @override_settings(MAX_CONCURRENT_PROMPT_PLATFORMS=3)
    def test_unavailable_client_falls_back_without_calling_the_handler(self):
        """No key / disabled provider yields the inert fallback stub."""
        called = []

        def _tracking_handler(prompt_text, user_domain, client, group):
            called.append('chatgpt')
            return {'fallback': False}

        self.processor._process_prompt_with_chatgpt = _tracking_handler

        with patch.object(self.processor, '_resolve_client', return_value=None):
            results = self._run(['chatgpt'])

        self.assertTrue(results['chatgpt'].get('fallback'))
        self.assertEqual(called, [], "handler ran despite there being no client")

    @override_settings(MAX_CONCURRENT_PROMPT_PLATFORMS=3)
    def test_clients_are_resolved_on_the_calling_thread(self):
        """
        The pool must never resolve clients: get_client() reads org settings via
        Redis with a DB fallback, and a Django connection opened on a pool thread
        is never closed. Regression guard for that specifically.
        """
        calling_thread = threading.get_ident()
        resolve_threads = []
        handler_threads = []

        def _record_resolve(provider, org_id):
            resolve_threads.append(threading.get_ident())
            return 'CLIENT'

        def _record_handler(prompt_text, user_domain, client, group):
            handler_threads.append(threading.get_ident())
            time.sleep(0.05)
            return {'fallback': False}

        self.processor._process_prompt_with_chatgpt = _record_handler
        self.processor._process_prompt_with_perplexity = _record_handler
        self.processor._process_prompt_with_claude = _record_handler

        with patch.object(self.processor, '_resolve_client', side_effect=_record_resolve):
            self._run(['chatgpt', 'perplexity', 'claude'])

        self.assertEqual(len(resolve_threads), 3)
        self.assertTrue(
            all(t == calling_thread for t in resolve_threads),
            "a client was resolved off the calling thread — that opens an unclosed DB connection"
        )
        # And the handlers genuinely did run somewhere else.
        self.assertTrue(
            any(t != calling_thread for t in handler_threads),
            "handlers never left the calling thread — the fan-out did not happen"
        )

    @override_settings(MAX_CONCURRENT_PROMPT_PLATFORMS=1)
    def test_max_workers_one_runs_serially_on_the_calling_thread(self):
        """The documented escape hatch back to the old behaviour."""
        calling_thread = threading.get_ident()
        handler_threads = []

        def _record_handler(prompt_text, user_domain, client, group):
            handler_threads.append(threading.get_ident())
            return {'fallback': False}

        self.processor._process_prompt_with_chatgpt = _record_handler
        self.processor._process_prompt_with_perplexity = _record_handler

        with patch.object(self.processor, '_resolve_client', return_value='CLIENT'):
            results = self._run(['chatgpt', 'perplexity'])

        self.assertEqual(len(results), 2)
        self.assertEqual(
            handler_threads, [calling_thread, calling_thread],
            "MAX_CONCURRENT_PROMPT_PLATFORMS=1 must not spawn threads"
        )

    @override_settings(MAX_CONCURRENT_PROMPT_PLATFORMS=3)
    def test_unknown_platform_falls_back_instead_of_raising(self):
        """An unrecognised ENABLED_PLATFORMS entry must not kill the prompt."""
        with patch.object(self.processor, '_resolve_client', return_value='CLIENT'):
            results = self._run(['chatgpt', 'not_a_real_platform'])

        self.assertTrue(results['not_a_real_platform'].get('fallback'))
        self.assertEqual(results['chatgpt']['platform_echo'], 'chatgpt')

    @override_settings(MAX_CONCURRENT_PROMPT_PLATFORMS=3)
    def test_empty_platform_list_is_a_noop(self):
        results = self._run([])
        self.assertEqual(results, {})
