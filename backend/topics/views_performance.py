"""
Topic performance — subject-level results read from the same rows as every other page.

Why this exists
---------------
Topic and TopicAnalytics store their own precomputed figures, produced by
TopicAnalyticsProcessor with maths that exists nowhere else in the product:
visibility as ``100 / avg_position``, and a mention counted whenever every
significant token of a keyword appears somewhere in a response. Neither matches
how Insights, Mentions or Citations measure the same ideas, so the Topics page
could never be reconciled against them and the numbers were not trusted.

This endpoint derives everything from ``PromptAnalytics`` — the rows the rest of
the product already reports on — by walking:

    Topic -> TopicKeyword -> Keyword -> PromptKeyword -> Prompt -> PromptAnalytics

and pulls competitors from ``CompetitorPromptAnalytics``, which hangs off the
same ``prompt`` foreign key, so a topic's rivals are measured over exactly the
same population as the brand.

The result answers the one question no other page can: which subject areas is
the brand contested on, and by whom. Prompt groups cannot aggregate across
themselves (a subject is usually split over several groups), and Insights only
reports domain-wide totals.

Nothing is written. Topic rows keep their stored values; this reads through them.
"""
import logging
from datetime import timedelta

import requests
from django.conf import settings

from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from competitors.models import CompetitorPromptAnalytics
from core.queryset_scoping import user_can_access_domain
from keywords.models import Keyword
from prompts.models import Prompt, PromptAnalytics

from .models import Topic

logger = logging.getLogger(__name__)

# Sentiment vocabulary shared by PromptAnalytics and CompetitorPromptAnalytics.
_CATEGORIES = ('positive', 'neutral', 'negative')


def _share(part, whole):
    return round(part * 100 / whole, 1) if whole else 0.0


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def topic_performance(request):
    """
    Per-topic brand and competitor performance for a domain.

    Query params:
        domain_id: Required
        days: Optional. Omit for all-time; pass a number to window by response date.
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    # 404 rather than 403: a 403 would confirm the domain exists.
    if not user_can_access_domain(request.user, domain_id, request):
        return Response({'error': 'Domain not found'}, status=status.HTTP_404_NOT_FOUND)

    days_param = request.query_params.get('days')
    since = None
    if days_param:
        try:
            since = timezone.now() - timedelta(days=int(days_param))
        except (TypeError, ValueError):
            since = None

    topics = list(Topic.objects.filter(domain_id=domain_id).order_by('name'))
    topic_ids = [t.id for t in topics]

    # Everything below is fetched in a fixed number of queries and grouped in
    # memory. The obvious per-topic loop issued roughly six queries per topic
    # and took over four seconds on a domain with twelve topics; prompts are
    # shared between topics anyway, so fetching once and bucketing is both
    # faster and avoids re-reading the same analytics rows repeatedly.

    # topic -> keyword ids
    keywords_by_topic = {tid: set() for tid in topic_ids}
    for tid, kid in Keyword.objects.filter(
        topic_keywords__topic_id__in=topic_ids
    ).values_list('topic_keywords__topic_id', 'id'):
        keywords_by_topic[tid].add(kid)

    all_keyword_ids = {kid for ids in keywords_by_topic.values() for kid in ids}

    # keyword -> prompt ids
    prompts_by_keyword = {}
    for kid, pid in Prompt.objects.filter(
        prompt_keywords__keyword_id__in=all_keyword_ids
    ).values_list('prompt_keywords__keyword_id', 'id'):
        prompts_by_keyword.setdefault(kid, set()).add(pid)

    prompts_by_topic = {
        tid: {pid for kid in kids for pid in prompts_by_keyword.get(kid, ())}
        for tid, kids in keywords_by_topic.items()
    }
    all_prompt_ids = {pid for pids in prompts_by_topic.values() for pid in pids}

    # One pass over the brand's responses for every prompt under any topic.
    analytics_qs = PromptAnalytics.objects.filter(
        prompt_id__in=all_prompt_ids, track_status='COMP'
    )
    if since:
        analytics_qs = analytics_qs.filter(created_at__gte=since)

    rows_by_prompt = {}
    for row in analytics_qs.values(
        'prompt_id', 'is_mention', 'position', 'sentiment_category', 'platform', 'citation_list'
    ):
        rows_by_prompt.setdefault(row['prompt_id'], []).append(row)

    # One pass over competitor mentions on the same prompts.
    competitor_qs = CompetitorPromptAnalytics.objects.filter(
        prompt_id__in=all_prompt_ids, is_mentioned=True
    )
    if since:
        competitor_qs = competitor_qs.filter(created_at__gte=since)

    competitors_by_prompt = {}
    for row in competitor_qs.values('prompt_id', 'competitor__name'):
        competitors_by_prompt.setdefault(row['prompt_id'], []).append(
            row['competitor__name'] or 'Unknown'
        )

    results = []
    for topic in topics:
        prompt_ids = prompts_by_topic.get(topic.id, set())
        keyword_count = len(keywords_by_topic.get(topic.id, ()))

        rows = [r for pid in prompt_ids for r in rows_by_prompt.get(pid, ())]
        responses = len(rows)
        mentioned = [r for r in rows if r['is_mention']]
        mentions = len(mentioned)

        # Position only where the brand appeared; 0 is the model default for
        # "no position", not a first-place finish.
        positions = [float(r['position']) for r in mentioned if r['position'] and r['position'] > 0]
        avg_position = sum(positions) / len(positions) if positions else None

        citations = sum(
            len(r['citation_list']) for r in rows if isinstance(r['citation_list'], list)
        )
        platforms = sorted({r['platform'] for r in rows if r['platform']})

        counts = {c: 0 for c in _CATEGORIES}
        for r in mentioned:
            category = (r['sentiment_category'] or 'neutral').lower()
            counts[category if category in counts else 'neutral'] += 1
        sentiment = {c: _share(counts[c], mentions) for c in _CATEGORIES}

        competitor_counts = {}
        for pid in prompt_ids:
            for name in competitors_by_prompt.get(pid, ()):
                competitor_counts[name] = competitor_counts.get(name, 0) + 1
        competitors = [
            {'name': name, 'mentions': n, 'mention_share': _share(n, responses)}
            for name, n in sorted(competitor_counts.items(), key=lambda kv: -kv[1])[:5]
        ]

        mention_share = _share(mentions, responses)

        # Opportunity: how much of a well-asked-about subject you are missing.
        # Volume alone rewards topics you already own; absence alone rewards
        # topics nobody asks about. The product ranks where work would change
        # something.
        opportunity = round(responses * (100 - mention_share) / 100, 1)

        results.append({
            'id': topic.id,
            'name': topic.name,
            'keywords': keyword_count,
            'prompts': len(prompt_ids),
            'responses': responses,
            'mentions': mentions,
            'mention_share': mention_share,
            'avg_position': round(avg_position, 2) if avg_position else None,
            'citations': citations,
            'sentiment': sentiment,
            'platforms': platforms,
            'competitors': competitors,
            'opportunity': opportunity,
        })

    # Biggest gap first — the page's default reading order should be "where to
    # act", not alphabetical.
    results.sort(key=lambda r: (-r['opportunity'], r['name']))

    totals = {
        'topics': len(results),
        'responses': sum(r['responses'] for r in results),
        'mentions': sum(r['mentions'] for r in results),
    }
    totals['mention_share'] = _share(totals['mentions'], totals['responses'])

    return Response({
        'days': int(days_param) if since else None,
        'source': 'prompt_analytics',
        'totals': totals,
        'results': results,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_topics(request):
    """
    Start topic generation for a domain.

    Topics are otherwise produced once, on the PROC -> COMP transition at the end
    of a domain's first prompt run. A domain past that point has no route to
    generate them, which is why the page could sit indefinitely on a "Processing
    topic data..." card describing work that was never queued.

    The run only reads keywords whose last_used_for_topic_generation is NULL and
    only ever inserts or merges — TopicProcessor performs no deletes — so this is
    safe to trigger on a domain that already has topics.

    Body:
        domain_id: Required
    """
    domain_id = request.data.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    # 404 rather than 403 so the response cannot confirm a domain exists.
    if not user_can_access_domain(request.user, domain_id, request):
        return Response({'error': 'Domain not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        engine_api_url = getattr(settings, 'ENGINE_API_URL', 'http://localhost:8001').rstrip('/')
        response = requests.post(
            f"{engine_api_url}/api/topics/generate/",
            json={'domain_id': int(domain_id)},
            timeout=15,
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"generate_topics: engine unreachable for domain {domain_id}: {e}")
        return Response(
            {'error': 'Could not reach the processing engine. Please try again shortly.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        payload = response.json()
    except ValueError:
        payload = {'error': 'Unexpected response from the processing engine.'}

    # 409 means every keyword is already grouped — an expected answer, not a
    # failure, so it is passed through for the UI to phrase properly.
    if response.status_code in (202, 409, 400, 404):
        return Response(payload, status=response.status_code)

    logger.error(f"generate_topics: engine returned {response.status_code} for domain {domain_id}")
    return Response(
        {'error': 'The processing engine rejected the request.'},
        status=status.HTTP_502_BAD_GATEWAY,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def topic_generation_status(request):
    """Progress of a running topic-grouping job, proxied from the engine.

    The page polls this so a refresh mid-run restores the progress bar. A run
    writes no rows until it finishes, so without it the UI cannot distinguish
    "grouping 812 keywords" from "never started" — and used to offer to start a
    second run over the same keywords.

    Query params:
        domain_id: Required
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    if not user_can_access_domain(request.user, domain_id, request):
        return Response({'error': 'Domain not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        engine_api_url = getattr(settings, 'ENGINE_API_URL', 'http://localhost:8001').rstrip('/')
        response = requests.get(
            f"{engine_api_url}/api/topics/generation-status/",
            params={'domain_id': int(domain_id)},
            timeout=10,
        )
    except requests.exceptions.RequestException as e:
        # An unreachable engine is not "no run in progress" — say unknown so the
        # page keeps whatever it was showing rather than flipping to idle and
        # inviting a duplicate run.
        logger.warning(f"topic_generation_status: engine unreachable for domain {domain_id}: {e}")
        return Response({'state': 'unknown', 'domain_id': int(domain_id)})

    if response.status_code != 200:
        return Response({'state': 'unknown', 'domain_id': int(domain_id)})

    try:
        return Response(response.json())
    except ValueError:
        return Response({'state': 'unknown', 'domain_id': int(domain_id)})
