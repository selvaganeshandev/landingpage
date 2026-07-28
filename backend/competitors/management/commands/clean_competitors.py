"""Repair or remove competitor records created by the old extraction logic.

Three faults produced them (all fixed in the engine as of 2026-07-28):

1. The brand label came from the FIRST hostname label rather than the
   registrable domain, so `kite.zerodha.com` became "Kite" — Zerodha's own
   trading product, recorded as its rival.
2. Only an exact host match against the brand's own domain was excluded, so its
   subdomains sailed through.
3. The URL was GUESSED as ``https://www.<name>.com`` and never verified, which
   is how `wikipedia.org` came to be stored as `wikipedia.com`. 274 of 279
   records (98%) carried a fabricated address.

This command classifies every existing competitor against the citations
actually recorded for its domain:

* **own**      — the name matches the domain's own brand (its subdomains) → delete
* **excluded** — a reference/community site nobody competes with → delete
* **repair**   — a real brand, but the stored URL was fabricated and a genuine
                 cited URL exists → rewrite the URL, keep the record and history
* **keep**     — nothing to do

Deleting cascades to that competitor's share-of-voice and analytics history,
which is intended: those rows describe a company that was never a competitor.
Runs as a dry run unless ``--apply`` is passed.
"""

from __future__ import annotations

import re
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from competitors.models import Competitor
from domains.models import Domain
from prompts.models import PromptAnalytics

# Kept in step with engine/core/analytics_helpers.py. Reference and community
# sites that get cited constantly and are not anybody's competitor.
EXCLUDED_LABELS = {
    'google', 'facebook', 'twitter', 'linkedin', 'instagram', 'youtube',
    'github', 'stackoverflow', 'wikipedia', 'medium', 'amazon', 'aws',
    'microsoft', 'apple', 'w3', 'mozilla', 'chrome', 'example', 'test',
    'localhost', 'schema', 'json', 'xml',
    'reddit', 'quora', 'wikimedia', 'wiktionary', 'britannica',
    'tripadvisor', 'yelp', 'glassdoor', 'crunchbase', 'bloomberg',
    'forbes', 'reuters', 'bbc', 'cnn', 'nytimes', 'wsj', 'economictimes',
    'timesofindia', 'hindustantimes', 'livemint', 'moneycontrol',
    'investopedia', 'yahoo', 'bing', 'duckduckgo', 'archive',
    'x', 'threads', 'tiktok', 'pinterest', 'substack', 'blogspot',
    'wordpress', 'wix', 'squarespace', 'shopify', 'gov', 'nic',
    'support', 'help', 'docs', 'blog', 'www', 'api', 'app', 'login',
}

TWO_PART_SUFFIXES = {
    'co.in', 'co.uk', 'com.au', 'co.nz', 'co.za', 'com.br', 'com.sg',
    'com.my', 'co.jp', 'or.jp', 'ne.jp', 'com.mx', 'co.id', 'com.tr',
}


def host_of(url: str) -> str:
    if not url:
        return ''
    host = re.sub(r'^https?://', '', url.strip(), flags=re.IGNORECASE)
    host = host.split('/')[0].split('?')[0].lower()
    if host.startswith('www.'):
        host = host[4:]
    return host.rstrip('.')


def registrable(host: str) -> str:
    host = host_of(host) if '://' in host or '/' in host else (host or '').lower().rstrip('.')
    if not host:
        return ''
    parts = host.split('.')
    if len(parts) < 2:
        return host
    if len(parts) >= 3 and '.'.join(parts[-2:]) in TWO_PART_SUFFIXES:
        return '.'.join(parts[-3:])
    return '.'.join(parts[-2:])


class Command(BaseCommand):
    help = "Repair or remove competitor records produced by the old extraction logic."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help="Actually write. Without it this is a dry run.")
        parser.add_argument('--domain-id', type=int, default=None)

    def handle(self, *args, **options):
        domains = Domain.objects.all()
        if options['domain_id']:
            domains = domains.filter(id=options['domain_id'])

        totals = Counter()
        to_delete, to_repair = [], []

        for domain in domains:
            competitors = list(Competitor.objects.filter(domain=domain))
            if not competitors:
                continue

            own = registrable(domain.url or '')
            own_label = own.split('.')[0] if own else ''
            cited = self._cited_hosts(domain)

            for c in competitors:
                totals['total'] += 1
                label = re.sub(r'[^a-z0-9]', '', (c.name or '').lower())
                fabricated = (c.url or '') == f'https://www.{label}.com'

                if own_label and label == own_label:
                    to_delete.append((domain, c, 'own brand'))
                    totals['own'] += 1
                    continue
                if label in EXCLUDED_LABELS:
                    to_delete.append((domain, c, 'reference site'))
                    totals['excluded'] += 1
                    continue

                real = cited.get(label)
                if fabricated and real:
                    to_repair.append((domain, c, f'https://{real}'))
                    totals['repair'] += 1
                elif fabricated:
                    # A fabricated URL with no matching citation: the brand was
                    # only ever seen as text, so the address is unverified.
                    totals['unverified'] += 1
                else:
                    totals['keep'] += 1

        self.stdout.write("")
        self.stdout.write(f"  total competitors        {totals['total']}")
        self.stdout.write(f"  delete — own brand       {totals['own']}")
        self.stdout.write(f"  delete — reference site  {totals['excluded']}")
        self.stdout.write(f"  repair URL from citation {totals['repair']}")
        self.stdout.write(f"  fabricated, unverifiable {totals['unverified']}")
        self.stdout.write(f"  already fine             {totals['keep']}")
        self.stdout.write("")

        for domain, c, why in to_delete[:15]:
            self.stdout.write(f"    DELETE  {domain.name[:18]:<20} {c.name[:18]:<20} ({why})")
        for domain, c, url in to_repair[:15]:
            self.stdout.write(f"    REPAIR  {domain.name[:18]:<20} {c.name[:18]:<20} {c.url} -> {url}")

        if not options['apply']:
            self.stdout.write(self.style.WARNING("\nDry run. Re-run with --apply to write."))
            return

        with transaction.atomic():
            for _domain, c, _why in to_delete:
                c.delete()
            for _domain, c, url in to_repair:
                c.url = url
                c.save(update_fields=['url'])

        self.stdout.write(self.style.SUCCESS(
            f"\nApplied: {len(to_delete)} deleted, {len(to_repair)} URLs repaired."))

    @staticmethod
    def _cited_hosts(domain):
        """{brand label -> registrable host} from URLs actually cited for this domain."""
        hosts = Counter()
        qs = PromptAnalytics.objects.filter(
            prompt__group__domain=domain
        ).values_list('citation_list', flat=True)
        for citation_list in qs:
            if not isinstance(citation_list, list):
                continue
            for entry in citation_list:
                url = None
                if isinstance(entry, dict):
                    for field in ('url', 'source', 'link', 'href', 'uri'):
                        value = entry.get(field)
                        if value and isinstance(value, str):
                            url = value
                            break
                elif isinstance(entry, str):
                    url = entry
                if url:
                    reg = registrable(host_of(url))
                    if reg:
                        hosts[reg] += 1

        out = {}
        for reg, _count in hosts.most_common():
            out.setdefault(reg.split('.')[0], reg)
        return out
