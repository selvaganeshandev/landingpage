"""
Tests for the raw GA4 / Search Console report proxies
(/integrations/google/ga4/run-report/ and /integrations/google/search-console/query/).

Google is never called: ``googleapiclient.discovery.build`` is patched and the
request body it would have sent is captured and asserted on. Covers:
  1. Query-param -> Google request body translation (metrics, dimensions,
     filters, ordering, paging, date defaults)
  2. Row flattening of the Google response
  3. Validation errors (missing domain_id, bad filter, bad date, bad limit)
  4. Integration state errors (missing, no property selected, no credentials)
  5. Google API failures surface as 502
  6. Service API key can read; cross-org domain is denied
"""
import hashlib
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIClient

from authentication.models import Account, Organisation, ServiceApiKey
from domains.models import Domain
from integrations.models import Integration

GA4_URL = '/integrations/google/ga4/run-report/'
GSC_URL = '/integrations/google/search-console/query/'

GA4_RESPONSE = {
    'dimensionHeaders': [{'name': 'landingPagePlusQueryString'}],
    'metricHeaders': [{'name': 'sessions'}, {'name': 'keyEvents'}],
    'rows': [
        {'dimensionValues': [{'value': '/pricing'}],
         'metricValues': [{'value': '120'}, {'value': '7'}]},
        {'dimensionValues': [{'value': '/blog/x'}],
         'metricValues': [{'value': '80'}, {'value': '0'}]},
    ],
    'rowCount': 2,
}

GSC_RESPONSE = {
    'rows': [
        {'keys': ['buy widgets', 'https://example.com/w'], 'clicks': 10,
         'impressions': 200, 'ctr': 0.05, 'position': 4.2},
    ],
}


def _org_user(suffix='', role='admin'):
    org = Organisation.objects.create(name=f'Org{suffix}')
    user = Account.objects.create_user(
        username=f'user{suffix}', email=f'user{suffix}@example.com',
        password='pw', organisation=org, role=role)
    return org, user


def _domain(org, suffix=''):
    return Domain.objects.create(
        name=f'Dom{suffix}', url=f'https://example{suffix}.com', organisation=org)


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


class _ProxyBase(TestCase):
    def setUp(self):
        self.org, self.user = _org_user()
        self.domain = _domain(self.org)
        self.ga = Integration.objects.create(
            domain=self.domain, type='google_analytics', provider_id='123456',
            credentials={'refresh_token': 'r'}, status='active', created_by=self.user)
        self.gsc = Integration.objects.create(
            domain=self.domain, type='search_console', provider_id='sc-domain:example.com',
            credentials={'refresh_token': 'r'}, status='active', created_by=self.user)
        self.client = _client(self.user)

    def _patch_google(self, response):
        """Patch credentials + discovery build; return (patcher, service_mock)."""
        service = MagicMock()
        # GA4: service.properties().runReport(...).execute()
        service.properties.return_value.runReport.return_value.execute.return_value = response
        # GSC: service.searchanalytics().query(...).execute()
        service.searchanalytics.return_value.query.return_value.execute.return_value = response
        creds = patch('integrations.google_proxy.get_credentials_from_integration',
                      return_value=MagicMock())
        build = patch('integrations.google_proxy.build', return_value=service)
        return creds, build, service


# ---------------------------------------------------------------------------
# GA4
# ---------------------------------------------------------------------------

class Ga4RunReportTests(_ProxyBase):

    def _run(self, params, response=GA4_RESPONSE):
        creds, build, service = self._patch_google(response)
        with creds, build:
            r = self.client.get(GA4_URL, params)
        call = service.properties.return_value.runReport.call_args
        return r, (call.kwargs if call else None)

    def test_translates_params_into_run_report_body(self):
        r, call = self._run({
            'domain_id': self.domain.id,
            'metrics': 'sessions,keyEvents',
            'dimensions': 'landingPagePlusQueryString',
            'start_date': '2026-08-01', 'end_date': '2026-08-31',
            'filter': 'sessionDefaultChannelGroup=Organic Search',
            'order_by': '-sessions',
            'limit': '50', 'offset': '100',
        })
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(call['property'], 'properties/123456')
        body = call['body']
        self.assertEqual(body['dateRanges'], [{'startDate': '2026-08-01', 'endDate': '2026-08-31'}])
        self.assertEqual(body['metrics'], [{'name': 'sessions'}, {'name': 'keyEvents'}])
        self.assertEqual(body['dimensions'], [{'name': 'landingPagePlusQueryString'}])
        self.assertEqual(body['limit'], 50)
        self.assertEqual(body['offset'], 100)
        self.assertEqual(body['dimensionFilter'], {'filter': {
            'fieldName': 'sessionDefaultChannelGroup',
            'stringFilter': {'value': 'Organic Search', 'matchType': 'EXACT'}}})
        self.assertEqual(body['orderBys'], [{'metric': {'metricName': 'sessions'}, 'desc': True}])

    def test_flattens_rows_and_reports_totals(self):
        r, _ = self._run({'domain_id': self.domain.id, 'metrics': 'sessions,keyEvents',
                          'dimensions': 'landingPagePlusQueryString'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['rows'], [
            {'landingPagePlusQueryString': '/pricing', 'sessions': 120.0, 'keyEvents': 7.0},
            {'landingPagePlusQueryString': '/blog/x', 'sessions': 80.0, 'keyEvents': 0.0},
        ])
        self.assertEqual(r.data['row_count'], 2)
        self.assertEqual(r.data['total_rows'], 2)
        self.assertEqual(r.data['property_id'], '123456')
        self.assertEqual(r.data['metrics'], ['sessions', 'keyEvents'])

    def test_defaults_when_only_domain_given(self):
        r, call = self._run({'domain_id': self.domain.id})
        self.assertEqual(r.status_code, 200)
        body = call['body']
        self.assertEqual(body['metrics'], [{'name': 'sessions'}])
        self.assertEqual(body['dimensions'], [])
        self.assertEqual(body['limit'], 1000)
        self.assertNotIn('dimensionFilter', body)
        self.assertNotIn('orderBys', body)
        start, end = body['dateRanges'][0]['startDate'], body['dateRanges'][0]['endDate']
        self.assertLess(start, end)

    def test_multiple_filters_are_and_grouped_and_negation_works(self):
        r, call = self._run({'domain_id': self.domain.id, 'dimensions': 'pagePath',
                             'filter': ['sessionDefaultChannelGroup=Organic Search',
                                        'pagePath!~^/admin']})
        self.assertEqual(r.status_code, 200)
        f = call['body']['dimensionFilter']
        self.assertIn('andGroup', f)
        exprs = f['andGroup']['expressions']
        self.assertEqual(len(exprs), 2)
        self.assertIn('notExpression', exprs[1])
        self.assertEqual(exprs[1]['notExpression']['filter']['stringFilter'],
                         {'value': '^/admin', 'matchType': 'FULL_REGEXP'})

    def test_filter_value_containing_other_operator_splits_on_earliest(self):
        r, call = self._run({'domain_id': self.domain.id, 'dimensions': 'pagePath',
                             'filter': 'pagePath=/a~b*c'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(call['body']['dimensionFilter']['filter']['stringFilter'],
                         {'value': '/a~b*c', 'matchType': 'EXACT'})

    def test_order_by_dimension_ascending(self):
        r, call = self._run({'domain_id': self.domain.id, 'dimensions': 'date',
                             'order_by': 'date'})
        self.assertEqual(call['body']['orderBys'],
                         [{'dimension': {'dimensionName': 'date'}, 'desc': False}])

    def test_limit_is_capped_at_google_maximum(self):
        r, call = self._run({'domain_id': self.domain.id, 'limit': '999999'})
        self.assertEqual(call['body']['limit'], 10000)

    def test_property_prefix_not_duplicated(self):
        self.ga.provider_id = 'properties/999'
        self.ga.save()
        r, call = self._run({'domain_id': self.domain.id})
        self.assertEqual(call['property'], 'properties/999')

    # -- validation ---------------------------------------------------------

    def test_missing_domain_id(self):
        r, call = self._run({})
        self.assertEqual(r.status_code, 400)
        self.assertIsNone(call)

    def test_bad_filter_syntax(self):
        r, call = self._run({'domain_id': self.domain.id, 'filter': 'nooperator'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('filter', r.data['error'])
        self.assertIsNone(call)

    def test_bad_date(self):
        r, call = self._run({'domain_id': self.domain.id, 'start_date': '08/01/2026'})
        self.assertEqual(r.status_code, 400)
        self.assertIsNone(call)

    def test_bad_limit(self):
        r, call = self._run({'domain_id': self.domain.id, 'limit': 'ten'})
        self.assertEqual(r.status_code, 400)
        self.assertIsNone(call)

    def test_too_many_metrics(self):
        r, call = self._run({'domain_id': self.domain.id,
                             'metrics': ','.join(f'm{i}' for i in range(11))})
        self.assertEqual(r.status_code, 400)
        self.assertIsNone(call)

    # -- integration state --------------------------------------------------

    def test_no_ga_integration(self):
        self.ga.delete()
        r, call = self._run({'domain_id': self.domain.id})
        self.assertEqual(r.status_code, 404)

    def test_inactive_integration(self):
        self.ga.status = 'disconnected'
        self.ga.save()
        r, _ = self._run({'domain_id': self.domain.id})
        self.assertEqual(r.status_code, 404)

    def test_no_property_selected(self):
        self.ga.provider_id = ''
        self.ga.save()
        r, _ = self._run({'domain_id': self.domain.id})
        self.assertEqual(r.status_code, 400)

    def test_no_credentials(self):
        with patch('integrations.google_proxy.get_credentials_from_integration', return_value=None), \
             patch('integrations.google_proxy.build') as build:
            r = self.client.get(GA4_URL, {'domain_id': self.domain.id})
        self.assertEqual(r.status_code, 400)
        build.assert_not_called()

    def test_google_http_error_is_502(self):
        from googleapiclient.errors import HttpError
        resp = MagicMock(status=429, reason='quota')
        service = MagicMock()
        service.properties.return_value.runReport.return_value.execute.side_effect = \
            HttpError(resp, b'{"error": {"message": "quota exceeded"}}')
        with patch('integrations.google_proxy.get_credentials_from_integration', return_value=MagicMock()), \
             patch('integrations.google_proxy.build', return_value=service):
            r = self.client.get(GA4_URL, {'domain_id': self.domain.id})
        self.assertEqual(r.status_code, 502)
        self.assertIn('Google Analytics API error', r.data['error'])


# ---------------------------------------------------------------------------
# Search Console
# ---------------------------------------------------------------------------

class GscSearchAnalyticsTests(_ProxyBase):

    def _run(self, params, response=GSC_RESPONSE):
        creds, build, service = self._patch_google(response)
        with creds, build:
            r = self.client.get(GSC_URL, params)
        call = service.searchanalytics.return_value.query.call_args
        return r, (call.kwargs if call else None)

    def test_translates_params_into_query_body(self):
        r, call = self._run({
            'domain_id': self.domain.id,
            'dimensions': 'query,page',
            'start_date': '2026-08-01', 'end_date': '2026-08-31',
            'filter': ['query!~(?i)example|exmpl', 'country=ind'],
            'search_type': 'web',
            'limit': '500', 'offset': '1000',
        })
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(call['siteUrl'], 'sc-domain:example.com')
        body = call['body']
        self.assertEqual(body['startDate'], '2026-08-01')
        self.assertEqual(body['endDate'], '2026-08-31')
        self.assertEqual(body['dimensions'], ['query', 'page'])
        self.assertEqual(body['rowLimit'], 500)
        self.assertEqual(body['startRow'], 1000)
        self.assertEqual(body['type'], 'web')
        self.assertEqual(body['dimensionFilterGroups'], [{'groupType': 'and', 'filters': [
            {'dimension': 'query', 'operator': 'excludingRegex', 'expression': '(?i)example|exmpl'},
            {'dimension': 'country', 'operator': 'equals', 'expression': 'ind'},
        ]}])

    def test_flattens_rows_with_dimension_names(self):
        r, _ = self._run({'domain_id': self.domain.id, 'dimensions': 'query,page'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['rows'], [{
            'query': 'buy widgets', 'page': 'https://example.com/w',
            'clicks': 10, 'impressions': 200, 'ctr': 0.05, 'position': 4.2,
        }])
        self.assertEqual(r.data['site_url'], 'sc-domain:example.com')
        self.assertEqual(r.data['row_count'], 1)

    def test_defaults(self):
        r, call = self._run({'domain_id': self.domain.id})
        self.assertEqual(r.status_code, 200)
        body = call['body']
        self.assertEqual(body['dimensions'], ['query'])
        self.assertEqual(body['rowLimit'], 1000)
        self.assertEqual(body['startRow'], 0)
        self.assertNotIn('dimensionFilterGroups', body)

    def test_contains_and_not_contains_operators(self):
        r, call = self._run({'domain_id': self.domain.id,
                             'filter': ['query*brand', 'page!*staging']})
        ops = [f['operator'] for f in call['body']['dimensionFilterGroups'][0]['filters']]
        self.assertEqual(ops, ['contains', 'notContains'])

    def test_limit_capped(self):
        r, call = self._run({'domain_id': self.domain.id, 'limit': '99999'})
        self.assertEqual(call['body']['rowLimit'], 25000)

    def test_bad_filter(self):
        r, call = self._run({'domain_id': self.domain.id, 'filter': 'query'})
        self.assertEqual(r.status_code, 400)
        self.assertIsNone(call)

    def test_no_gsc_integration(self):
        self.gsc.delete()
        r, _ = self._run({'domain_id': self.domain.id})
        self.assertEqual(r.status_code, 404)

    def test_pending_site_selection(self):
        self.gsc.provider_id = 'pending_selection'
        self.gsc.save()
        r, _ = self._run({'domain_id': self.domain.id})
        self.assertEqual(r.status_code, 400)

    def test_google_http_error_is_502(self):
        from googleapiclient.errors import HttpError
        service = MagicMock()
        service.searchanalytics.return_value.query.return_value.execute.side_effect = \
            HttpError(MagicMock(status=403, reason='forbidden'), b'{}')
        with patch('integrations.google_proxy.get_credentials_from_integration', return_value=MagicMock()), \
             patch('integrations.google_proxy.build', return_value=service):
            r = self.client.get(GSC_URL, {'domain_id': self.domain.id})
        self.assertEqual(r.status_code, 502)


# ---------------------------------------------------------------------------
# Auth / scoping
# ---------------------------------------------------------------------------

class ProxyAccessTests(_ProxyBase):

    def setUp(self):
        super().setUp()
        # Mirrors service_key_views._service_account: role 'client' keeps the
        # key read-only, is_service_account widens reads to the whole org.
        self.service = Account.objects.create_user(
            username='svc', email='svc@example.com', password='pw',
            organisation=self.org, role='client', is_service_account=True)
        self.raw = 'pmxk_test_' + 'x' * 20
        ServiceApiKey.objects.create(
            organisation=self.org, service_account=self.service, created_by=self.user,
            name='ext', key_hash=hashlib.sha256(self.raw.encode()).hexdigest(),
            key_prefix='pmxk_...xxxx')

    def _api(self):
        # Real header so ApiKeyAuthentication and DomainAccessMiddleware both run.
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Api-Key {self.raw}')
        return c

    def test_anonymous_denied(self):
        r = APIClient().get(GA4_URL, {'domain_id': self.domain.id})
        self.assertIn(r.status_code, (401, 403))

    def test_service_api_key_can_read_ga4(self):
        creds, build, _ = self._patch_google(GA4_RESPONSE)
        with creds, build:
            r = self._api().get(GA4_URL, {'domain_id': self.domain.id})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['row_count'], 2)

    def test_service_api_key_can_read_gsc(self):
        creds, build, _ = self._patch_google(GSC_RESPONSE)
        with creds, build:
            r = self._api().get(GSC_URL, {'domain_id': self.domain.id})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['row_count'], 1)

    def test_other_org_domain_denied_for_api_key(self):
        # DomainAccessMiddleware answers 404 for a domain outside the org so
        # the response does not confirm the domain exists.
        other_org, other_user = _org_user('2')
        other_domain = _domain(other_org, '2')
        Integration.objects.create(
            domain=other_domain, type='google_analytics', provider_id='777',
            credentials={'refresh_token': 'r'}, status='active', created_by=other_user)
        creds, build, service = self._patch_google(GA4_RESPONSE)
        with creds, build:
            r = self._api().get(GA4_URL, {'domain_id': other_domain.id})
        self.assertEqual(r.status_code, 404)
        service.properties.return_value.runReport.assert_not_called()
