"""
Raw GA4 / Search Console report proxies.

The SEO Reports module returns fixed, pre-shaped sheets. External consumers
(service API keys, other apps) sometimes need a data point those sheets do not
compute — conversions by landing page, key events by query, a custom brand
regex — without a new sheet type each time. These two endpoints forward a
caller-described report to Google using the domain's stored integration
credentials and return the rows as-is.

Both are GET-only so a service API key (client role, safe methods only) can
call them, and both take ``domain_id`` in the query string so
DomainAccessMiddleware scopes them like every other read.

Nothing here writes to Google: the OAuth scopes are read-only.
"""
import logging
from datetime import datetime, timedelta

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .google_oauth import get_credentials_from_integration
from .models import Integration

logger = logging.getLogger(__name__)

GA4_DEFAULT_LIMIT = 1000
GA4_MAX_LIMIT = 10000        # GA4 Data API hard cap per runReport
GSC_DEFAULT_LIMIT = 1000
GSC_MAX_LIMIT = 25000        # Search Console hard cap per query

# ``filter=<field><op><value>`` — first operator that matches wins, so the
# two-character operators are listed before their one-character prefixes.
_GA4_FILTER_OPS = [
    ('!~', ('FULL_REGEXP', True)),   # exclude regex
    ('~', ('FULL_REGEXP', False)),   # include regex
    ('*', ('CONTAINS', False)),      # contains
    ('^', ('BEGINS_WITH', False)),   # begins with
    ('=', ('EXACT', False)),         # exact
]
_GSC_FILTER_OPS = [
    ('!~', 'excludingRegex'),
    ('~', 'includingRegex'),
    ('!*', 'notContains'),
    ('*', 'contains'),
    ('!=', 'notEquals'),
    ('=', 'equals'),
]


def _csv(value):
    return [v.strip() for v in (value or '').split(',') if v.strip()]


def _int_param(params, name, default, maximum):
    raw = params.get(name)
    if raw in (None, ''):
        return default, None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, f'{name} must be an integer'
    if value < 0:
        return None, f'{name} must be >= 0'
    return min(value, maximum), None


def _date_range(params, lag_days):
    """Default window: the 30 days ending ``lag_days`` ago (Google data lags)."""
    end_date = params.get('end_date')
    start_date = params.get('start_date')
    if not end_date:
        end_date = (datetime.now() - timedelta(days=lag_days)).strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
    for label, value in (('start_date', start_date), ('end_date', end_date)):
        try:
            datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return None, None, f'{label} must be YYYY-MM-DD'
    return start_date, end_date, None


def _split_filter(raw, ops):
    """Split ``field<op>value`` on the earliest operator; None if no operator.

    Earliest wins so a value containing another operator's character
    (``query=a~b``) still splits on ``=``. Two-character operators sit one
    index before their one-character suffix, so ``!~`` beats ``~`` on a tie.
    """
    best = None
    for op, spec in ops:
        idx = raw.find(op)
        if idx > 0 and (best is None or idx < best[0]):
            best = (idx, op, spec)
    if best is None:
        return None
    idx, op, spec = best
    return raw[:idx].strip(), spec, raw[idx + len(op):]


def _get_integration(domain_id, integration_type):
    integration = Integration.objects.filter(
        domain_id=domain_id, type=integration_type, status='active'
    ).first()
    if not integration:
        return None, None, Response(
            {'error': f'{integration_type} integration not found or not active'},
            status=status.HTTP_404_NOT_FOUND,
        )
    if not integration.provider_id or integration.provider_id in ('', 'pending_selection'):
        return None, None, Response(
            {'error': 'Integration has no property/site selected'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    credentials = get_credentials_from_integration(integration)
    if not credentials:
        return None, None, Response(
            {'error': 'No valid credentials found'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return integration, credentials, None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ga4_run_report(request):
    """
    Proxy a GA4 Data API ``runReport`` for a domain's connected property.

    Query params:
        - domain_id   (required)
        - metrics     comma-separated GA4 metric names (default: sessions)
        - dimensions  comma-separated GA4 dimension names (optional)
        - start_date / end_date  YYYY-MM-DD (default: 30 days ending yesterday)
        - filter      repeatable, ``<dimension><op><value>``; all AND-ed.
                      ops: ``=`` exact, ``*`` contains, ``^`` begins with,
                      ``~`` regex, ``!~`` exclude regex.
                      e.g. filter=sessionDefaultChannelGroup=Organic Search
        - order_by    metric or dimension name; prefix ``-`` for descending
        - limit       rows (default 1000, max 10000)
        - offset      row offset for paging

    Returns rows as ``{dimension: value, metric: number}`` dicts.
    """
    params = request.query_params
    domain_id = params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    metrics = _csv(params.get('metrics')) or ['sessions']
    dimensions = _csv(params.get('dimensions'))
    if len(metrics) > 10 or len(dimensions) > 9:
        return Response(
            {'error': 'GA4 allows at most 10 metrics and 9 dimensions per report'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    start_date, end_date, err = _date_range(params, lag_days=1)
    if err:
        return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
    limit, err = _int_param(params, 'limit', GA4_DEFAULT_LIMIT, GA4_MAX_LIMIT)
    if err:
        return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
    offset, err = _int_param(params, 'offset', 0, 10 ** 9)
    if err:
        return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

    expressions = []
    for raw in params.getlist('filter'):
        parsed = _split_filter(raw, _GA4_FILTER_OPS)
        if not parsed:
            return Response(
                {'error': f'filter "{raw}" needs one of = * ^ ~ !~ between field and value'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        field, (match_type, negate), value = parsed
        expr = {'filter': {'fieldName': field,
                           'stringFilter': {'value': value, 'matchType': match_type}}}
        expressions.append({'notExpression': expr} if negate else expr)

    body = {
        'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
        'metrics': [{'name': m} for m in metrics],
        'dimensions': [{'name': d} for d in dimensions],
        'limit': limit,
        'offset': offset,
    }
    if expressions:
        body['dimensionFilter'] = (expressions[0] if len(expressions) == 1
                                   else {'andGroup': {'expressions': expressions}})
    order_by = (params.get('order_by') or '').strip()
    if order_by:
        desc = order_by.startswith('-')
        name = order_by.lstrip('-')
        key = ({'metric': {'metricName': name}} if name in metrics
               else {'dimension': {'dimensionName': name}})
        body['orderBys'] = [{**key, 'desc': desc}]

    integration, credentials, err_response = _get_integration(domain_id, 'google_analytics')
    if err_response:
        return err_response
    property_id = integration.provider_id
    if not property_id.startswith('properties/'):
        property_id = f'properties/{property_id}'

    try:
        service = build('analyticsdata', 'v1beta', credentials=credentials)
        response = service.properties().runReport(property=property_id, body=body).execute()
    except HttpError as e:
        logger.error("GA4 runReport proxy error domain=%s: %s", domain_id, e)
        return Response({'error': f'Google Analytics API error: {e}'},
                        status=status.HTTP_502_BAD_GATEWAY)
    except Exception as e:
        logger.error("GA4 runReport proxy failed domain=%s: %s", domain_id, e)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    dim_headers = [h['name'] for h in response.get('dimensionHeaders', [])]
    met_headers = [h['name'] for h in response.get('metricHeaders', [])]
    rows = []
    for row in response.get('rows', []):
        item = {dim_headers[i]: v['value'] for i, v in enumerate(row.get('dimensionValues', []))}
        for i, v in enumerate(row.get('metricValues', [])):
            try:
                item[met_headers[i]] = float(v['value'])
            except (TypeError, ValueError):
                item[met_headers[i]] = v['value']
        rows.append(item)

    return Response({
        'success': True,
        'property_id': integration.provider_id,
        'date_range': {'start': start_date, 'end': end_date},
        'dimensions': dim_headers,
        'metrics': met_headers,
        'rows': rows,
        'row_count': len(rows),
        'total_rows': response.get('rowCount', len(rows)),
        'offset': offset,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gsc_search_analytics(request):
    """
    Proxy a Search Console ``searchAnalytics.query`` for a domain's site.

    Query params:
        - domain_id   (required)
        - dimensions  comma-separated: query, page, country, device, date,
                      searchAppearance (default: query)
        - start_date / end_date  YYYY-MM-DD (default: 30 days ending 3 days ago)
        - filter      repeatable, ``<dimension><op><value>``; all AND-ed.
                      ops: ``=`` equals, ``!=`` notEquals, ``*`` contains,
                      ``!*`` notContains, ``~`` includingRegex, ``!~`` excludingRegex.
                      e.g. filter=query!~(?i)mybrand|my brand
        - search_type web (default), image, video, news, discover, googleNews
        - limit       rows (default 1000, max 25000)
        - offset      row offset (startRow) for paging

    Returns rows as ``{dimension: value, clicks, impressions, ctr, position}``.
    """
    params = request.query_params
    domain_id = params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    dimensions = _csv(params.get('dimensions')) or ['query']
    start_date, end_date, err = _date_range(params, lag_days=3)
    if err:
        return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
    limit, err = _int_param(params, 'limit', GSC_DEFAULT_LIMIT, GSC_MAX_LIMIT)
    if err:
        return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
    offset, err = _int_param(params, 'offset', 0, 10 ** 9)
    if err:
        return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

    filters = []
    for raw in params.getlist('filter'):
        parsed = _split_filter(raw, _GSC_FILTER_OPS)
        if not parsed:
            return Response(
                {'error': f'filter "{raw}" needs one of = != * !* ~ !~ between dimension and value'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        dimension, operator, value = parsed
        filters.append({'dimension': dimension, 'operator': operator, 'expression': value})

    body = {
        'startDate': start_date,
        'endDate': end_date,
        'dimensions': dimensions,
        'rowLimit': limit,
        'startRow': offset,
        'type': params.get('search_type') or 'web',
    }
    if filters:
        body['dimensionFilterGroups'] = [{'groupType': 'and', 'filters': filters}]

    integration, credentials, err_response = _get_integration(domain_id, 'search_console')
    if err_response:
        return err_response

    try:
        service = build('searchconsole', 'v1', credentials=credentials)
        response = service.searchanalytics().query(
            siteUrl=integration.provider_id, body=body
        ).execute()
    except HttpError as e:
        logger.error("GSC query proxy error domain=%s: %s", domain_id, e)
        return Response({'error': f'Search Console API error: {e}'},
                        status=status.HTTP_502_BAD_GATEWAY)
    except Exception as e:
        logger.error("GSC query proxy failed domain=%s: %s", domain_id, e)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    rows = []
    for row in response.get('rows', []):
        item = dict(zip(dimensions, row.get('keys', [])))
        item.update({
            'clicks': row.get('clicks', 0),
            'impressions': row.get('impressions', 0),
            'ctr': row.get('ctr', 0),
            'position': row.get('position', 0),
        })
        rows.append(item)

    return Response({
        'success': True,
        'site_url': integration.provider_id,
        'date_range': {'start': start_date, 'end': end_date},
        'dimensions': dimensions,
        'rows': rows,
        'row_count': len(rows),
        'offset': offset,
    })
