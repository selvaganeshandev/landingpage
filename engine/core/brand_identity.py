"""How the product decides that a brand was named in an AI answer.

This used to be three near-identical blocks of `sld.replace(' ', '-')` in
analytics_helpers.py, all fed the domain's DISPLAY NAME and all treating that
name as if it were a hostname. That failed for any brand whose name carries a
word its URL does not:

    name  'CanaraHSBCLife Insurance'   ->  canarahsbclife insurance
                                          canarahsbclifeinsurance
                                          canarahsbclife-insurance
    answer 'Canara HSBC Life Insurance ...'   -> no pattern matches

Domain 40 recorded 972 completed rows, 87 of which contained the brand in the
response text, and every one of them was stored as is_mention=False: visibility
0, share of voice 0%, "no AI presence" reported to a paying client that has one.
Citations failed harder still — the "hostname" contained a space, and the URL
regex excludes whitespace, so it could never match any URL at all.

The fix is to stop guessing from one string. A brand has two identities and both
are authoritative:

  * the URL it owns          canarahsbclife.com  -> the label `canarahsbclife`
  * the name people write it as   'CanaraHSBCLife Insurance'

Splitting the name into words (on spaces AND on camel-case humps) gives
['canara', 'hsbc', 'life', 'insurance'], and joining those with an optional
separator matches every spelling an LLM actually produces — 'Canara HSBC Life
Insurance', 'CanaraHSBCLife Insurance', 'canara-hsbc-life-insurance'. Segmenting
the URL label with the same words yields 'canara hsbc life', which is how the
brand is usually named in prose.

Deliberately free of Django so it can be tested without a database or settings:
    python tests/standalone/engine/core/test_brand_identity.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Sequence, Tuple
from urllib.parse import urlparse


# Two-part public suffixes seen in this product's markets. Without these,
# "example.co.in" yields a registrable domain of "co.in" and every Indian site
# collapses to the same bogus brand.
#
# The `.in` second-level zones are not decoration: three tracked domains live on
# `bank.in` (iob.bank.in, kotak811.bank.in, hsbc.bank.in). Missing that entry
# made the registrable domain "bank.in" and the brand label the bare word
# "bank" — a pattern that matches every banking answer ever written, which is a
# worse failure than the one this module fixes.
TWO_PART_SUFFIXES = {
    'co.in', 'co.uk', 'com.au', 'co.nz', 'co.za', 'com.br', 'com.sg',
    'com.my', 'co.jp', 'or.jp', 'ne.jp', 'com.mx', 'co.id', 'com.tr',
    'bank.in', 'net.in', 'org.in', 'gen.in', 'firm.in', 'ind.in',
    'ac.in', 'edu.in', 'res.in', 'gov.in', 'nic.in', 'mil.in',
    'org.uk', 'ac.uk', 'gov.uk', 'net.au', 'org.au', 'edu.au',
}

# A pattern shorter than this matches half the dictionary. Kept from the code
# this module replaces so short brands behave exactly as they did before.
MIN_PATTERN_LENGTH = 3

# What may sit between two words of the brand in prose. Bounded rather than `*`
# so "…canara. Meanwhile HSBC…" cannot be joined into a single false mention.
_PROSE_SEPARATOR = r'[\s\-_.]{0,3}'

# The same idea inside a URL, where whitespace cannot occur.
_URL_SEPARATOR = r'[-_.]{0,2}'

# Trailing characters that end a URL in prose rather than belong to it.
_URL_BODY = r'[^\s\)\]]*'

_CAMEL_SPLIT = re.compile(r'[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|\d+')
_NON_ALNUM = re.compile(r'[^0-9A-Za-z]+')


def host_from_value(value: str) -> str:
    """Hostname for a URL, or '' when the value is not one.

    Accepts the bare-host form ('zerodha.com') the database mostly stores as
    well as a full URL. A display name with no dot in it is NOT a host, and
    returning '' for it is the point: the caller then knows it has only a name
    to work with instead of silently treating 'CanaraHSBCLife Insurance' as a
    hostname, which is the bug this module exists to fix.
    """
    if not value:
        return ''
    try:
        parsed = urlparse(value if '://' in value else f'http://{value}')
        host = (parsed.netloc or parsed.path or '').strip().lower()
    except Exception:
        host = str(value).strip().lower()
    host = host.split('/')[0].split('?')[0]
    if host.startswith('www.'):
        host = host[4:]
    if ':' in host:
        host = host.split(':', 1)[0]
    host = host.rstrip('.')
    if '.' not in host or ' ' in host:
        return ''
    return host


def registrable_domain(host: str) -> str:
    """eTLD+1 for a hostname, e.g. kite.zerodha.com -> zerodha.com.

    Splitting on the FIRST label instead (the old behaviour) turned a brand's
    own subdomains into competitors: kite.zerodha.com became "Kite", and
    support./coin.zerodha.com became "Support" and "Coin" — Zerodha's own
    products, recorded as its rivals.
    """
    host = (host or '').lower().strip().rstrip('.')
    if not host:
        return ''
    parts = host.split('.')
    if len(parts) < 2:
        return host
    if len(parts) >= 3 and '.'.join(parts[-2:]) in TWO_PART_SUFFIXES:
        return '.'.join(parts[-3:])
    return '.'.join(parts[-2:])


def brand_label(host: str) -> str:
    """The registrable name without its suffix: kite.zerodha.co.in -> zerodha."""
    registrable = registrable_domain(host)
    return registrable.split('.')[0] if registrable else ''


def tokenise(value: str) -> List[str]:
    """Words of a brand name, splitting on punctuation AND camel-case humps.

    'CanaraHSBCLife Insurance' -> ['canara', 'hsbc', 'life', 'insurance']
    'Grown Brilliance'         -> ['grown', 'brilliance']
    'Zerodha'                  -> ['zerodha']

    The camel-case split is what recovers the spacing the writer of the name
    omitted, and it is the reason an answer saying 'Canara HSBC Life' can be
    matched against a name stored as 'CanaraHSBCLife'.
    """
    tokens: List[str] = []
    for chunk in _NON_ALNUM.split(value or ''):
        if chunk:
            tokens.extend(part.lower() for part in _CAMEL_SPLIT.findall(chunk))
    return tokens


def _segment_label(label: str, tokens: Sequence[str]) -> List[str]:
    """Split a URL label into words using the brand name's words.

    'canarahsbclife' with ['canara','hsbc','life','insurance'] -> the first
    three, which is how the brand is named in prose.

    The label is compared without its punctuation, so 'paradise-kerala' still
    segments against ['paradise','kerala']. A trailing remainder is allowed to
    match a PREFIX of the next name word, so 'merillife' against
    ['meril','lifesciences'] yields ['meril','life'] — the abbreviation the
    company itself uses — rather than giving up.

    Returns [] when the name does not spell the label at all, which is the
    signal to fall back to the label as a single word.
    """
    normalised = _NON_ALNUM.sub('', (label or '').lower())
    if not normalised or not tokens:
        return []
    consumed: List[str] = []
    rest = normalised
    for token in tokens:
        if not rest:
            break
        if rest.startswith(token):
            consumed.append(token)
            rest = rest[len(token):]
            continue
        # Last chance: the label abbreviates this word ('life' of 'lifesciences').
        if len(rest) >= MIN_PATTERN_LENGTH and token.startswith(rest):
            consumed.append(rest)
            rest = ''
            break
        return []
    return consumed if not rest else []


def _phrase_regex(tokens: Sequence[str], separator: str) -> str:
    return separator.join(re.escape(token) for token in tokens)


def _dedupe(sequences: Sequence[Sequence[str]]) -> List[Tuple[str, ...]]:
    seen = set()
    out: List[Tuple[str, ...]] = []
    for seq in sequences:
        key = tuple(seq)
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


@dataclass(frozen=True)
class BrandIdentity:
    """Everything needed to recognise one brand in one block of text."""

    name: str
    host: str
    label: str
    word_groups: Tuple[Tuple[str, ...], ...]
    _mention_res: Tuple[re.Pattern, ...]
    _url_res: Tuple[re.Pattern, ...]

    @property
    def is_resolvable(self) -> bool:
        """False when neither a usable URL nor a usable name was supplied."""
        return bool(self._mention_res)

    def mention_count(self, text: str) -> int:
        """Non-overlapping mentions of the brand.

        Spans are deduplicated across patterns so 'canarahsbclife.com' counted
        by both the host pattern and the word pattern is one mention, not two.
        """
        if not text or not self._mention_res:
            return 0
        spans: List[Tuple[int, int]] = []
        for regex in self._mention_res:
            for match in regex.finditer(text):
                span = match.span()
                if any(not (span[1] <= s or span[0] >= e) for s, e in spans):
                    continue
                spans.append(span)
        return len(spans)

    def appears_in(self, text: str) -> bool:
        if not text or not self._mention_res:
            return False
        return any(regex.search(text) for regex in self._mention_res)

    def citation_urls(self, text: str) -> List[str]:
        """URLs in `text` that belong to the brand, deduplicated, in order."""
        if not text or not self._url_res:
            return []
        found: List[str] = []
        seen = set()
        for regex in self._url_res:
            for match in regex.finditer(text):
                url = match.group(0)
                if url not in seen:
                    seen.add(url)
                    found.append(url)
        return found


@lru_cache(maxsize=512)
def build_brand_identity(domain_value: str, brand_name: str = '') -> BrandIdentity:
    """Resolve a brand from the URL it owns and the name people write it as.

    Either argument may be empty or wrong-way-round: a `domain_value` with no
    dot is treated as a name, which keeps every legacy caller that passed
    `domain.name` working instead of silently producing zero matches.
    """
    domain_value = (domain_value or '').strip()
    brand_name = (brand_name or '').strip()

    host = host_from_value(domain_value)
    if not host:
        host = host_from_value(brand_name)
        # `domain_value` was not a URL, so it can only have been a name.
        if domain_value and not brand_name:
            brand_name = domain_value
        elif domain_value and domain_value != brand_name and not host:
            brand_name = brand_name or domain_value

    label = brand_label(host)
    name_tokens = tokenise(brand_name)

    # The brand as prose: every word of the name, separators optional.
    groups: List[Sequence[str]] = []
    if name_tokens:
        groups.append(name_tokens)

    # The brand as its URL spells it, spaced back out where the name allows.
    # This is the pattern that catches 'Canara HSBC Life' — the form the model
    # writes most often, which neither the raw name nor the raw label matches.
    if label:
        segmented = _segment_label(label, name_tokens)
        groups.append(segmented if segmented else [label])

    groups = _dedupe(groups)
    groups = [g for g in groups if len(''.join(g)) >= MIN_PATTERN_LENGTH]

    mention_sources = [
        r'\b' + _phrase_regex(group, _PROSE_SEPARATOR) + r'\b'
        for group in groups
    ]
    # The hostname itself, so 'visit canarahsbclife.com' counts as a mention.
    if host:
        mention_sources.append(r'\b' + re.escape(host) + r'\b')

    url_sources = []
    if host:
        url_sources.append(_URL_BODY + re.escape(host) + _URL_BODY)
    for group in groups:
        # Separators are applied to the REGEX, never to an already-escaped
        # string. Building it the other way round — re.escape(label.replace(...))
        # — is what turned the old optional-separator class into the literal
        # text `\[\-_\]\?`, so no URL ever matched it.
        url_sources.append(
            _URL_BODY + _phrase_regex(group, _URL_SEPARATOR) + _URL_BODY
        )

    def _compile(sources: Sequence[str], prefix: str = '') -> Tuple[re.Pattern, ...]:
        compiled = []
        for source in sources:
            try:
                compiled.append(re.compile(prefix + source, re.IGNORECASE))
            except re.error:
                continue
        return tuple(compiled)

    return BrandIdentity(
        name=brand_name,
        host=host,
        label=label,
        word_groups=tuple(tuple(g) for g in groups),
        _mention_res=_compile(mention_sources),
        _url_res=_compile(url_sources, prefix=r'https?://'),
    )
