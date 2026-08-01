"""
Diagnose the DataBlue /v1/scrape fallback used by link validation.

The endpoint's schema is not published, so this command exists to answer three
questions without editing code: is the key accepted, what does a response
actually look like, and does `datablue_scrape._interpret` read it correctly.

    python manage.py check_datablue_scrape https://www.acra.gov.sg
    python manage.py check_datablue_scrape https://example.com/gone --raw

Run it once against a URL you know is live and once against a known 404. If the
verdicts come back INCONCLUSIVE with a readable payload, the field names in
`_STATUS_KEYS` / `_CONTENT_KEYS` need widening to match what DataBlue returns —
the payload printed by --raw tells you exactly which keys to add.
"""
import json

from django.conf import settings
from django.core.management.base import BaseCommand

from misinformation.services import datablue_scrape
from misinformation.services.link_validator import LinkValidator


class Command(BaseCommand):
    help = "Check the DataBlue /v1/scrape link-validation fallback against a URL"

    def add_arguments(self, parser):
        parser.add_argument("url", help="URL to test")
        parser.add_argument(
            "--raw",
            action="store_true",
            help="Print the full JSON response so unknown field names can be identified",
        )

    def handle(self, *args, **options):
        url = options["url"]

        key = getattr(settings, "DATABLUE_API_KEY", "")
        endpoint = getattr(settings, "DATABLUE_SCRAPE_URL", datablue_scrape.DEFAULT_SCRAPE_URL)
        enabled = getattr(settings, "MISINFO_DATABLUE_FALLBACK", True)

        self.stdout.write("Configuration")
        self.stdout.write(f"  endpoint : {endpoint}")
        self.stdout.write(f"  key      : {'set (' + key[:6] + '…)' if key else 'MISSING'}")
        self.stdout.write(f"  fallback : {'enabled' if enabled else 'disabled'}")
        self.stdout.write("")

        if not datablue_scrape.is_enabled():
            self.stdout.write(self.style.WARNING(
                "Fallback is off (no key or MISINFO_DATABLUE_FALLBACK=False). "
                "Validation will use HEAD-only verdicts."
            ))
            return

        if options["raw"]:
            self._dump_raw(url, endpoint, key)

        verdict, status_code, error = datablue_scrape.check_url(url)
        label = {
            True: self.style.SUCCESS("VALID — page loads"),
            False: self.style.ERROR("BROKEN"),
            None: self.style.WARNING("INCONCLUSIVE — caller keeps its own verdict"),
        }[verdict]

        self.stdout.write("DataBlue verdict")
        self.stdout.write(f"  result   : {label}")
        self.stdout.write(f"  status   : {status_code}")
        self.stdout.write(f"  error    : {error}")
        self.stdout.write("")

        # End-to-end: what the scan would actually record for this URL.
        is_valid, code, err = LinkValidator().validate(url)
        self.stdout.write("Full LinkValidator result (HEAD + fallback)")
        self.stdout.write(f"  is_valid : {is_valid}")
        self.stdout.write(f"  status   : {code}")
        self.stdout.write(f"  error    : {err}")

    def _dump_raw(self, url, endpoint, key):
        """Show the untouched response so unknown keys can be spotted."""
        import requests

        try:
            resp = requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={getattr(settings, "DATABLUE_SCRAPE_URL_FIELD", "url"): url},
                timeout=getattr(settings, "DATABLUE_SCRAPE_TIMEOUT", 30),
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Request failed: {e}"))
            self.stdout.write("")
            return

        self.stdout.write(f"Raw response (HTTP {resp.status_code})")
        try:
            payload = resp.json()
            # Top-level keys first — that is what _STATUS_KEYS/_CONTENT_KEYS must match.
            if isinstance(payload, dict):
                self.stdout.write(f"  top-level keys: {sorted(payload.keys())}")
            body = json.dumps(payload, indent=2)[:2000]
        except ValueError:
            body = resp.text[:2000]
        self.stdout.write(body)
        self.stdout.write("")
