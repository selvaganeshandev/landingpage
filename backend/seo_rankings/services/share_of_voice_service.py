"""
Share of Voice — how much of the tracked market's search results we own.

Built entirely from data already stored. For every tracked keyword,
`SeoKeywordRank.snippets_details['competitors']` holds the full results page:
every rival domain with its position, title and URL. Measured on the largest
account, that is present on 1,765 of 1,765 keywords, ~29 results each, covering
positions 1-30, across 2,061 distinct domains.

Our own domain is NOT in that dict — our slot is the gap in the sequence. On a
400-keyword sample, `rank_now` sat exactly in that gap 396 times (the other 4
had no gap, i.e. we rank below the stored depth). So the complete results page
is the rivals dict plus our own `rank_now`, and this module reconstructs it that
way rather than trusting either source alone.

No writes, no migrations.
"""
from urllib.parse import urlparse

# Visibility weight by position. Positions 1-20 reuse the CTR curve the
# Opportunities score is built on, so the two features cannot disagree about
# what a position is worth. 21-30 are extrapolated small values — by then a
# result earns almost nothing, but zero would wrongly erase a domain that is
# present across hundreds of pages.
from .opportunities_service import CTR_BY_POSITION

TAIL_WEIGHT = {21: 0.005, 22: 0.005, 23: 0.004, 24: 0.004, 25: 0.003,
               26: 0.003, 27: 0.003, 28: 0.002, 29: 0.002, 30: 0.002}
POSITION_WEIGHT = {**CTR_BY_POSITION, **TAIL_WEIGHT}

# Deepest position the scrape stores.
MAX_POSITION = 30

# Domains that take real estate but are not commercial rivals. They are not
# removed — they genuinely occupy the results page and pretending otherwise
# would overstate our share — but they are flagged so the UI can separate
# "a competitor is beating us" from "this query returns videos".
NON_RIVAL_DOMAINS = {
    'youtube.com', 'm.youtube.com', 'youtu.be',
    'wikipedia.org', 'en.wikipedia.org',
    'facebook.com', 'instagram.com', 'linkedin.com', 'twitter.com', 'x.com',
    'reddit.com', 'quora.com', 'pinterest.com',
    'amazon.com', 'amazon.in', 'flipkart.com',
    'play.google.com', 'apps.apple.com',
}

# Government, regulator and academic sites. On this account these are among the
# highest-scoring domains (incometax.gov.in alone holds ~9%), and nobody can
# outrank a tax authority on its own statute — treating them as competitors
# would make the league table advice-free.
NON_RIVAL_SUFFIXES = ('.gov', '.gov.in', '.nic.in', '.edu', '.ac.in', '.nih.gov', '.org.in')


def _is_non_rival(host):
    return host in NON_RIVAL_DOMAINS or host.endswith(NON_RIVAL_SUFFIXES)

DEFAULT_TOP_N = 25


def _weight(position):
    if not position or position < 1 or position > MAX_POSITION:
        return 0.0
    return POSITION_WEIGHT.get(position, 0.0)


def _normalise_domain(value):
    """Strip scheme, www. and any path so 'https://www.x.com/a' -> 'x.com'."""
    if not value:
        return ''
    value = value.strip().lower()
    if '://' in value:
        value = urlparse(value).netloc or value
    value = value.split('/')[0]
    if value.startswith('www.'):
        value = value[4:]
    return value


def _our_domain(domain):
    return _normalise_domain(getattr(domain, 'url', '') or getattr(domain, 'name', ''))


def _tracked_competitor_domains(domain_id):
    from ..models import SeoCompetitorProject
    return {
        _normalise_domain(d)
        for d in SeoCompetitorProject.objects
        .filter(domain_id=domain_id)
        .values_list('competitor_domain', flat=True)
        if d
    }


def build_share_of_voice(domain_id, platform='desktop', top_n=DEFAULT_TOP_N):
    """
    Volume-weighted visibility share for us and every rival domain seen in our
    tracked results pages.

    A domain's score is the sum over every tracked keyword of
    `search_volume x weight(position)`. Weighting by volume is what makes this a
    business number rather than a count of appearances — ranking #3 for a term
    nobody searches is not visibility.
    """
    from ..models import SeoKeywordRank
    from domains.models import Domain

    domain = Domain.objects.filter(id=domain_id).first()
    ours = _our_domain(domain) if domain else ''
    tracked = _tracked_competitor_domains(domain_id)

    rows = (
        SeoKeywordRank.objects
        .filter(domain_id=domain_id, platform=platform)
        .select_related('keyword')
        .only('id', 'rank_now', 'search_volume', 'snippets_details', 'keyword__keyword')
    )

    our_points = 0.0
    total_points = 0.0
    stats = {}                 # domain -> accumulated metrics
    keywords_analysed = 0
    keywords_with_volume = 0
    our_appearances = 0
    volume_total = 0

    for kw in rows:
        competitors = (kw.snippets_details or {}).get('competitors')
        if not isinstance(competitors, dict) or not competitors:
            continue

        volume = kw.search_volume or 0
        keywords_analysed += 1
        if volume:
            keywords_with_volume += 1
            volume_total += volume

        # Our own contribution. rank_now of 0 means we are not in the results
        # at all, which correctly earns nothing.
        our_kw_points = volume * _weight(kw.rank_now)
        if kw.rank_now and kw.rank_now <= MAX_POSITION:
            our_appearances += 1
        our_points += our_kw_points
        total_points += our_kw_points

        for key, entry in competitors.items():
            if not isinstance(entry, dict):
                continue
            host = _normalise_domain(entry.get('domain') or entry.get('url'))
            if not host or host == ours:
                continue
            try:
                position = int(entry.get('rank') or key)
            except (TypeError, ValueError):
                continue

            points = volume * _weight(position)
            total_points += points

            s = stats.setdefault(host, {
                'domain': host,
                'points': 0.0,
                'appearances': 0,
                'position_sum': 0,
                'best_position': None,
                'beats_us': 0,
                'we_beat': 0,
                'we_are_absent': 0,
            })
            s['points'] += points
            s['appearances'] += 1
            s['position_sum'] += position
            if s['best_position'] is None or position < s['best_position']:
                s['best_position'] = position

            if not kw.rank_now:
                s['we_are_absent'] += 1
            elif position < kw.rank_now:
                s['beats_us'] += 1
            else:
                s['we_beat'] += 1

    def share(points):
        return round((points / total_points * 100), 2) if total_points else 0.0

    competitors_out = []
    for s in stats.values():
        competitors_out.append({
            'domain': s['domain'],
            'share': share(s['points']),
            'appearances': s['appearances'],
            'avg_position': round(s['position_sum'] / s['appearances'], 1),
            'best_position': s['best_position'],
            'beats_us': s['beats_us'],
            'we_beat': s['we_beat'],
            'we_are_absent': s['we_are_absent'],
            'is_tracked': s['domain'] in tracked,
            'is_non_rival': _is_non_rival(s['domain']),
        })
    competitors_out.sort(key=lambda c: -c['share'])

    # Where we sit in the visibility league table. A bare "0.82%" reads as a
    # failure when it is simply what one domain's share looks like against
    # 2,000 others; the position is the number that means something.
    our_position = 1 + sum(1 for s in stats.values() if s['points'] > our_points)

    # Share measured only against genuine commercial rivals — excluding search
    # features, marketplaces and government sites nobody can outrank. This is
    # the figure that belongs at the top of a client report.
    rival_points = sum(
        s['points'] for s in stats.values() if not _is_non_rival(s['domain'])
    )
    rival_total = rival_points + our_points
    our_share_vs_rivals = round(our_points / rival_total * 100, 2) if rival_total else 0.0

    # Rivals with real visibility that nobody has added as a competitor.
    untracked = [
        c for c in competitors_out
        if not c['is_tracked'] and not c['is_non_rival']
    ][:10]

    return {
        'our_domain': ours,
        'our_share': share(our_points),
        'our_share_vs_rivals': our_share_vs_rivals,
        'our_position': our_position,
        'competitors': competitors_out[:top_n],
        'untracked_rivals': untracked,
        'summary': {
            'keywords_analysed': keywords_analysed,
            'keywords_with_volume': keywords_with_volume,
            'volume_covered': volume_total,
            'rival_domains_seen': len(stats),
            'our_appearances': our_appearances,
            'tracked_competitors': len(tracked),
        },
        'method': (
            'Volume-weighted: each domain scores search volume x a '
            'position weight, summed across every tracked keyword. Position '
            'weights are published average click-through rates, not measured '
            'for this site.'
        ),
    }
