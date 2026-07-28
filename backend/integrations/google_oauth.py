"""
Google OAuth 2.0 integration for Google Analytics and Search Console.
"""
import json
import logging
from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .ai_platforms import AI_SOURCE_REGEX, resolve_platform

from .models import Integration
from .utils.reconnect import preserved_provider_id
from domains.models import Domain, DomainAccess

logger = logging.getLogger(__name__)

# Google OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/analytics.readonly',  # GA4 Data API
    'https://www.googleapis.com/auth/webmasters.readonly',  # Search Console
]

# Frontend URL for redirect after OAuth
FRONTEND_URL = getattr(settings, 'SITE_URL', '')


def get_google_oauth_config():
    """Get Google OAuth configuration from settings."""
    return {
        'client_id': getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', ''),
        'client_secret': getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', ''),
        'redirect_uri': getattr(settings, 'GOOGLE_OAUTH_REDIRECT_URI', ''),
    }


def create_oauth_flow(state=None):
    """Create a Google OAuth flow."""
    config = get_google_oauth_config()

    client_config = {
        'web': {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': [config['redirect_uri']],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=config['redirect_uri']
    )

    if state:
        flow.state = state

    return flow


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def google_auth_url(request):
    """
    Generate Google OAuth authorization URL.
    Query params:
        - domain_id: The domain to connect the integration to
        - integration_type: 'google_analytics' or 'search_console'
    """
    domain_id = request.query_params.get('domain_id')
    secondary_id = request.query_params.get('secondary_id')
    integration_type = request.query_params.get('integration_type', 'google_analytics')

    # Create state parameter with integration_type and user_id, plus EITHER a
    # domain_id (normal connect) OR a secondary_id (report-only subdomain connect).
    state_data = {
        'integration_type': integration_type,
        'user_id': request.user.id,
    }

    if secondary_id:
        # Report-only secondary subdomain: verify access via its primary domain.
        from seo_rankings.models import SeoSecondaryDomain
        secondary = SeoSecondaryDomain.objects.filter(pk=secondary_id).first()
        if not secondary:
            return Response({'error': 'Secondary subdomain not found'},
                            status=status.HTTP_404_NOT_FOUND)
        primary_id = secondary.primary_domain_id
        try:
            if request.user.role == 'super_admin':
                Domain.objects.get(pk=primary_id, organisation=request.user.organisation)
            else:
                DomainAccess.objects.get(
                    user=request.user, domain_id=primary_id,
                    domain__organisation=request.user.organisation,
                )
        except (Domain.DoesNotExist, DomainAccess.DoesNotExist):
            return Response({'error': 'Domain not found or access denied'},
                            status=status.HTTP_404_NOT_FOUND)
        state_data['secondary_id'] = secondary_id
    else:
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify user has access to the domain
        try:
            if request.user.role == 'super_admin':
                domain = Domain.objects.get(pk=domain_id, organisation=request.user.organisation)
            else:
                domain_access = DomainAccess.objects.get(
                    user=request.user,
                    domain_id=domain_id,
                    domain__organisation=request.user.organisation
                )
                domain = domain_access.domain
        except (Domain.DoesNotExist, DomainAccess.DoesNotExist):
            return Response(
                {'error': 'Domain not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        state_data['domain_id'] = domain_id

    # `popup=1` marks an OAuth started from a popup window (e.g. the Configure
    # Report page's secondary-subdomain connect): the callback then closes the
    # popup and notifies the opener instead of doing a full-page redirect.
    if str(request.query_params.get('popup', '')).lower() in ('1', 'true', 'yes'):
        state_data['popup'] = True
    state = json.dumps(state_data)

    try:
        flow = create_oauth_flow()
        authorization_url, _ = flow.authorization_url(
            access_type='offline',  # Get refresh token
            include_granted_scopes='true',
            prompt='consent',  # Force consent to get refresh token
            state=state
        )

        return Response({
            'authorization_url': authorization_url,
            'state': state
        })
    except Exception as e:
        logger.error(f"Error generating Google auth URL: {str(e)}")
        return Response(
            {'error': f'Failed to generate authorization URL: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _state_is_popup(state):
    """Best-effort: was this OAuth started from a popup window?"""
    try:
        return bool(json.loads(state).get('popup'))
    except Exception:
        return False


def _popup_close_response(message):
    """HTML page that posts the OAuth result back to the opener window and
    closes itself. Used instead of a redirect when the flow ran in a popup.
    """
    from django.http import HttpResponse
    target = FRONTEND_URL if FRONTEND_URL else '*'
    msg_json = json.dumps({'source': 'google-oauth', **message})
    html = (
        "<!doctype html><html><body>"
        "<script>"
        "try{if(window.opener){window.opener.postMessage("
        + msg_json + "," + json.dumps(target) + ");}}catch(e){}"
        "window.close();"
        "document.write('Connection complete \\u2014 you can close this window.');"
        "</script></body></html>"
    )
    return HttpResponse(html)


@api_view(['GET'])
@permission_classes([AllowAny])  # OAuth callback doesn't have auth header
def google_callback(request):
    """
    Handle Google OAuth callback.
    This endpoint receives the authorization code from Google and exchanges it for tokens.
    """
    code = request.query_params.get('code')
    state = request.query_params.get('state')
    error = request.query_params.get('error')
    is_popup = _state_is_popup(state) if state else False

    def _fail(error_code):
        """Return to the opener (popup) or the settings page (redirect)."""
        if is_popup:
            return _popup_close_response({'success': False, 'error': error_code})
        return redirect(f'{FRONTEND_URL}/organization-settings?error={error_code}')

    if error:
        logger.error(f"Google OAuth error: {error}")
        return _fail('google_auth_denied')

    if not code or not state:
        return _fail('missing_params')

    try:
        # Parse state to get the anchor (domain_id OR secondary_id) + type
        state_data = json.loads(state)
        domain_id = state_data.get('domain_id')
        secondary_id = state_data.get('secondary_id')
        integration_type = state_data.get('integration_type', 'google_analytics')
        user_id = state_data.get('user_id')

        if not user_id or (not domain_id and not secondary_id):
            return _fail('invalid_state')

        # Exchange code for tokens
        flow = create_oauth_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Resolve the anchor: a real Domain, or a report-only secondary subdomain.
        domain = None
        secondary = None
        if secondary_id:
            from seo_rankings.models import SeoSecondaryDomain
            secondary = SeoSecondaryDomain.objects.filter(pk=secondary_id).first()
            if not secondary:
                return _fail('domain_not_found')
        else:
            try:
                domain = Domain.objects.get(pk=domain_id)
            except Domain.DoesNotExist:
                return _fail('domain_not_found')

        # Get the user
        from authentication.models import Account
        try:
            user = Account.objects.get(pk=user_id)
        except Account.DoesNotExist:
            return _fail('user_not_found')

        # Store credentials
        credentials_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': list(credentials.scopes) if credentials.scopes else SCOPES,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
        }

        # Get property/site info based on integration type
        provider_id = ''  # Empty until property/site is selected
        integration_status = 'active'
        
        if integration_type == 'google_analytics':
            # Try to get GA4 properties
            try:
                properties = get_ga4_properties(credentials)
                if properties and len(properties) > 0:
                    # Properties found - store them, user will select one
                    credentials_data['available_properties'] = properties
                    integration_status = 'active'  # Keep active, user can select property
                else:
                    # No properties found - mark as disconnected
                    integration_status = 'disconnected'
                    credentials_data['error_message'] = 'No Google Analytics properties found for this account'
                    logger.warning(f"No GA4 properties found for user {user_id}")
            except Exception as e:
                # Error fetching properties - mark as disconnected
                integration_status = 'disconnected'
                credentials_data['error_message'] = f'Failed to fetch properties: {str(e)}'
                logger.error(f"Error fetching GA4 properties: {e}")
        elif integration_type == 'search_console':
            # Try to get GSC sites
            try:
                sites = fetch_gsc_sites_from_api(credentials)
                if sites and len(sites) > 0:
                    # Sites found - store them, user will select one
                    credentials_data['available_sites'] = sites
                    integration_status = 'active'  # Keep active, user can select site
                else:
                    # No sites found - mark as disconnected
                    integration_status = 'disconnected'
                    credentials_data['error_message'] = 'No Google Search Console sites found for this account'
                    logger.warning(f"No GSC sites found for user {user_id}")
            except Exception as e:
                # Error fetching sites - mark as disconnected
                integration_status = 'disconnected'
                credentials_data['error_message'] = f'Failed to fetch sites: {str(e)}'
                logger.error(f"Error fetching GSC sites: {e}")

        # Create or update integration. For a report-only secondary subdomain the
        # integration is anchored on `secondary_domain` (domain stays NULL) so it
        # never appears in primary-domain queries, lists, or processing.
        lookup = {'secondary_domain': secondary} if secondary else {'domain': domain}

        # These defaults are applied on UPDATE as well as CREATE, so an empty
        # provider_id would wipe the user's selected property/site every time
        # they press "Connect" again on an already-connected domain. The sync
        # schedulers skip any integration with an empty provider_id, so that
        # silently stops all tracking. Keep the existing selection when the
        # reconnected account still exposes it.
        existing = Integration.objects.filter(type=integration_type, **lookup).first()
        if existing:
            available = credentials_data.get('available_properties')
            if available is None:
                available = credentials_data.get('available_sites')
            provider_id = preserved_provider_id(
                existing.provider_id,
                available,
                fetch_succeeded=(integration_status == 'active'),
            )
            if existing.provider_id and not provider_id:
                logger.info(
                    f"Reconnect for integration {existing.id} ({integration_type}): previously "
                    f"selected '{existing.provider_id}' is no longer available to this account — "
                    "clearing so the user re-selects."
                )

        integration, created = Integration.objects.update_or_create(
            type=integration_type,
            **lookup,
            defaults={
                'provider_id': provider_id,
                'credentials': credentials_data,
                'status': integration_status,
                'last_sync_at': timezone.now(),
                'error_message': credentials_data.get('error_message'),
                'created_by': user,
            }
        )

        # Popup flow (e.g. secondary-subdomain connect on the report page):
        # close the popup and notify the opener — no full-page redirect, so the
        # half-filled report form in the opener window is preserved. The opener
        # then loads the property/site list and shows the selection dialog.
        if is_popup:
            return _popup_close_response({
                'success': True,
                'integration_type': integration_type,
                'domain_id': domain_id,
                'secondary_id': secondary_id,
                'integration_id': integration.id,
                'status': integration_status,
            })

        # Redirect back to frontend with success and actual status
        redirect_url = f'{FRONTEND_URL}/organization-settings/domains/{domain_id}?tab=integrations&success=google_connected&type={integration_type}&status={integration_status}'
        return redirect(redirect_url)

    except json.JSONDecodeError:
        return _fail('invalid_state')
    except Exception as e:
        logger.error(f"Error in Google OAuth callback: {str(e)}")
        return _fail('oauth_failed')


def _parse_stored_expiry(raw_expiry):
    """Parse the stored ISO expiry into the naive-UTC datetime google-auth expects.

    The expiry was always written to the credentials JSON but never read back, so
    google-auth saw expiry=None, considered the token valid forever, never
    refreshed proactively, and let calls fail instead.
    """
    if not raw_expiry:
        return None
    try:
        expiry = datetime.fromisoformat(raw_expiry)
    except (TypeError, ValueError):
        logger.warning(f"Unparseable stored token expiry: {raw_expiry!r}")
        return None
    if expiry.tzinfo is not None:
        expiry = expiry.astimezone(dt_timezone.utc).replace(tzinfo=None)
    return expiry


def _persist_refreshed_credentials(integration, credentials):
    """Write a newly refreshed access token back onto the integration.

    Without this the refreshed token is discarded when the request ends, so the
    stored token stays stale forever and the integration survives only on its
    refresh token — if a reconnect ever returns no new refresh token, auth dies
    with no path back.
    """
    try:
        creds_data = dict(integration.credentials or {})
        creds_data['token'] = credentials.token
        creds_data['expiry'] = credentials.expiry.isoformat() if credentials.expiry else None
        integration.credentials = creds_data
        integration.save(update_fields=['credentials'])
        logger.info(f"Refreshed and stored Google access token for integration {integration.id}")
    except Exception as e:
        # A failed write must not break the caller — the in-memory credentials
        # are still usable for this request.
        logger.warning(f"Could not persist refreshed token for integration {integration.id}: {e}")


def get_credentials_from_integration(integration, persist=True):
    """Convert stored credentials back to Google Credentials object.

    Refreshes the access token when it has expired and, unless persist=False,
    stores the new token so later requests reuse it.
    """
    creds_data = integration.credentials
    if not creds_data:
        return None

    credentials = Credentials(
        token=creds_data.get('token'),
        refresh_token=creds_data.get('refresh_token'),
        token_uri=creds_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=creds_data.get('client_id'),
        client_secret=creds_data.get('client_secret'),
        scopes=creds_data.get('scopes', SCOPES),
        expiry=_parse_stored_expiry(creds_data.get('expiry')),
    )

    if persist and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(GoogleAuthRequest())
            _persist_refreshed_credentials(integration, credentials)
        except Exception as e:
            # Let the caller proceed and surface the real API error; a refresh
            # failure here usually means the grant was revoked.
            logger.warning(f"Token refresh failed for integration {integration.id}: {e}")

    return credentials


def get_ga4_properties(credentials):
    """Get list of GA4 properties the user has access to."""
    try:
        service = build('analyticsadmin', 'v1beta', credentials=credentials)
        accounts = service.accounts().list().execute()

        properties = []
        for account in accounts.get('accounts', []):
            account_name = account['name']  # e.g., 'accounts/123456'
            props = service.properties().list(filter=f"parent:{account_name}").execute()
            for prop in props.get('properties', []):
                properties.append({
                    'id': prop['name'],  # e.g., 'properties/123456789'
                    'display_name': prop.get('displayName', ''),
                    'property_type': prop.get('propertyType', ''),
                    'account': account.get('displayName', ''),
                })

        return properties
    except HttpError as e:
        logger.error(f"Error fetching GA4 properties: {e}")
        raise


def fetch_gsc_sites_from_api(credentials):
    """Get list of Google Search Console sites the user has access to."""
    try:
        service = build('searchconsole', 'v1', credentials=credentials)
        sites = service.sites().list().execute()
        
        site_list = []
        for site in sites.get('siteEntry', []):
            site_list.append({
                'id': site.get('siteUrl', ''),  # e.g., 'sc-domain:example.com' or 'https://example.com/'
                'display_name': site.get('siteUrl', '').replace('sc-domain:', '').replace('https://', '').replace('http://', '').rstrip('/'),
                'permission_level': site.get('permissionLevel', ''),
                'verification_status': site.get('verificationStatus', ''),
            })
        
        return site_list
    except HttpError as e:
        logger.error(f"Error fetching GSC sites: {e}")
        raise


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ga_properties(request):
    """Get list of GA4 properties for a connected integration."""
    integration_id = request.query_params.get('integration_id')
    domain_id = request.query_params.get('domain_id')

    if not integration_id and not domain_id:
        return Response(
            {'error': 'integration_id or domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        if integration_id:
            integration = Integration.objects.get(
                pk=integration_id,
                type='google_analytics'
            )
        else:
            integration = Integration.objects.get(
                domain_id=domain_id,
                type='google_analytics'
            )

        # Check if we have cached properties
        cached_properties = integration.credentials.get('available_properties')
        if cached_properties:
            return Response({'properties': cached_properties})

        # Fetch fresh properties
        credentials = get_credentials_from_integration(integration)
        if not credentials:
            return Response(
                {'error': 'No valid credentials found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        properties = get_ga4_properties(credentials)

        # Cache the properties
        integration.credentials['available_properties'] = properties
        integration.save()

        return Response({'properties': properties})

    except Integration.DoesNotExist:
        return Response(
            {'error': 'Integration not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error fetching GA properties: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def select_ga_property(request):
    """Select a GA4 property for the integration."""
    integration_id = request.data.get('integration_id')
    property_id = request.data.get('property_id')
    property_name = request.data.get('property_name', '')

    if not integration_id or not property_id:
        return Response(
            {'error': 'integration_id and property_id are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        integration = Integration.objects.get(
            pk=integration_id,
            type='google_analytics'
        )

        # Update the provider_id with the selected property
        integration.provider_id = property_id
        integration.credentials['selected_property_name'] = property_name
        integration.save()

        # Create INIT record for processing — ONLY for real domains. A report-only
        # secondary subdomain (domain IS NULL) must not enter the GA processing
        # scheduler; its data is fetched live at report time instead.
        if integration.domain_id:
            from datetime import date, timedelta
            from .models import GATrafficInsight

            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            GATrafficInsight.objects.get_or_create(
                integration=integration,
                domain=integration.domain,
                start_date=start_date,
                end_date=end_date,
                defaults={
                    'track_status': 'INIT',
                }
            )

        return Response({
            'success': True,
            'message': f'Property {property_name} selected successfully'
        })

    except Integration.DoesNotExist:
        return Response(
            {'error': 'Integration not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_gsc_sites(request):
    """Get list of Google Search Console sites for a connected integration."""
    integration_id = request.query_params.get('integration_id')
    domain_id = request.query_params.get('domain_id')

    if not integration_id and not domain_id:
        return Response(
            {'error': 'integration_id or domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        if integration_id:
            integration = Integration.objects.get(
                pk=integration_id,
                type='search_console'
            )
        else:
            integration = Integration.objects.get(
                domain_id=domain_id,
                type='search_console'
            )

        # Check if we have cached sites
        cached_sites = integration.credentials.get('available_sites')
        if cached_sites:
            return Response({'sites': cached_sites})

        # Fetch fresh sites
        credentials = get_credentials_from_integration(integration)
        if not credentials:
            return Response(
                {'error': 'No valid credentials found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        sites = fetch_gsc_sites_from_api(credentials)

        # Cache the sites
        integration.credentials['available_sites'] = sites
        integration.save()

        return Response({'sites': sites})

    except Integration.DoesNotExist:
        return Response(
            {'error': 'Integration not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error fetching GSC sites: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def select_gsc_site(request):
    """Select a Google Search Console site for the integration."""
    integration_id = request.data.get('integration_id')
    site_id = request.data.get('site_id')
    site_name = request.data.get('site_name', '')

    if not integration_id or not site_id:
        return Response(
            {'error': 'integration_id and site_id are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        integration = Integration.objects.get(
            pk=integration_id,
            type='search_console'
        )

        # Update the provider_id with the selected site
        integration.provider_id = site_id
        integration.credentials['selected_site_name'] = site_name
        integration.save()

        # Create INIT record for processing — ONLY for real domains. A report-only
        # secondary subdomain (domain IS NULL) must not enter the GSC processing
        # scheduler; its data is fetched live at report time instead.
        if integration.domain_id:
            from datetime import date, timedelta
            from .models import GSCTrafficInsight

            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            GSCTrafficInsight.objects.get_or_create(
                integration=integration,
                domain=integration.domain,
                start_date=start_date,
                end_date=end_date,
                defaults={
                    'track_status': 'INIT',
                }
            )

        return Response({
            'success': True,
            'message': f'Site {site_name} selected successfully'
        })

    except Integration.DoesNotExist:
        return Response(
            {'error': 'Integration not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ga_data(request):
    """
    Fetch Google Analytics data for a domain.
    Query params:
        - domain_id: The domain to get data for
        - start_date: Start date (YYYY-MM-DD), defaults to 30 days ago
        - end_date: End date (YYYY-MM-DD), defaults to today
        - metrics: Comma-separated metrics (default: sessions,totalUsers,screenPageViews)
    """
    domain_id = request.query_params.get('domain_id')
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Default date range: last 30 days
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    try:
        integration = Integration.objects.get(
            domain_id=domain_id,
            type='google_analytics',
            status='active'
        )

        if not integration.provider_id or integration.provider_id == '':
            return Response({
                'error': 'Please select a GA4 property first',
                'needs_property_selection': True,
                'available_properties': integration.credentials.get('available_properties', [])
            }, status=status.HTTP_400_BAD_REQUEST)

        credentials = get_credentials_from_integration(integration)
        if not credentials:
            return Response(
                {'error': 'No valid credentials found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build GA4 Data API service
        service = build('analyticsdata', 'v1beta', credentials=credentials)

        # Extract property ID (remove 'properties/' prefix if present)
        property_id = integration.provider_id
        if not property_id.startswith('properties/'):
            property_id = f'properties/{property_id}'

        # Run report
        response = service.properties().runReport(
            property=property_id,
            body={
                'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                'metrics': [
                    {'name': 'sessions'},
                    {'name': 'totalUsers'},
                    {'name': 'screenPageViews'},
                    {'name': 'bounceRate'},
                    {'name': 'averageSessionDuration'},
                ],
                'dimensions': [
                    {'name': 'date'},
                ],
                'orderBys': [
                    {'dimension': {'dimensionName': 'date'}}
                ]
            }
        ).execute()

        # Parse response
        data = parse_ga_response(response)

        # Update last sync time
        integration.last_sync_at = timezone.now()
        integration.save()

        return Response({
            'success': True,
            'data': data,
            'date_range': {'start': start_date, 'end': end_date},
            'property_id': integration.provider_id,
            'property_name': integration.credentials.get('selected_property_name', ''),
        })

    except Integration.DoesNotExist:
        return Response(
            {'error': 'Google Analytics integration not found or not active'},
            status=status.HTTP_404_NOT_FOUND
        )
    except HttpError as e:
        logger.error(f"Google Analytics API error: {e}")
        return Response(
            {'error': f'Google Analytics API error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        logger.error(f"Error fetching GA data: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# GA4 enforces a per-property hourly report quota. The dashboard re-fetches the
# AI-referral endpoints on every load (and can storm them on re-renders), so
# without caching a busy property exhausts its quota and 429s constantly. The
# window "ends yesterday", so the data is settled — a short cache is safe and
# stops repeated loads from each hitting GA4.
AI_REFERRAL_CACHE_TTL = 15 * 60   # 15 min: reuse a successful GA4 result across reloads
AI_REFERRAL_ERROR_TTL = 2 * 60    # 2 min: negative-cache a 429 so it doesn't spawn MORE GA4 calls


def _ai_referral_cache_key(prefix, domain_id, start_date, end_date, days, platform=None):
    return f"{prefix}:v1:{domain_id}:{start_date}:{end_date}:{days}:{platform or ''}"


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ai_referral_data(request):
    """
    Fetch traffic data specifically from AI platforms.

    Matches the same sessionSource regex GA4's Explorations use, so the numbers
    reconcile with GA4. Accepts ?days=7|14|21|28 (default 28) for the lookback
    windows the team compares, or explicit ?start_date=&end_date=.

    Cached for AI_REFERRAL_CACHE_TTL so repeated dashboard loads reuse one GA4
    call instead of exhausting the property's hourly quota.
    """
    domain_id = request.query_params.get('domain_id')
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    days_param = request.query_params.get('days')

    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Date range resolution. To match GA4's "Last N days" comparison views we
    # use a window that ENDS YESTERDAY (GA4 treats today as an incomplete day
    # and excludes it from those presets) and report RAW session counts — no
    # proration — so the totals line up exactly with what the team sees in GA4.
    days = None
    if not (start_date and end_date):
        try:
            days = int(days_param) if days_param else 28
        except (TypeError, ValueError):
            days = 28
        window_end = datetime.now().date() - timedelta(days=1)   # yesterday
        window_start = window_end - timedelta(days=days - 1)
        end_date = window_end.strftime('%Y-%m-%d')
        start_date = window_start.strftime('%Y-%m-%d')

    cache_key = _ai_referral_cache_key('ai_referral', domain_id, start_date, end_date, days)
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached['body'], status=cached.get('status', status.HTTP_200_OK))

    try:
        integration = Integration.objects.get(
            domain_id=domain_id,
            type='google_analytics',
            status='active'
        )

        # Served from ga_ai_traffic_daily, not from GA4. The nightly
        # sync_ai_traffic command owns the fetching; keeping it off the request
        # path is what stops the traffic tabs 429-ing on GA4's hourly quota and
        # what makes the figures survive a disconnected integration.
        _ensure_traffic_synced(domain_id, days)
        _start = datetime.strptime(start_date, '%Y-%m-%d').date()
        _end = datetime.strptime(end_date, '%Y-%m-%d').date()
        body = _build_ai_traffic_body(domain_id, _start, _end, days)
        cache.set(cache_key, {'body': body}, AI_REFERRAL_CACHE_TTL)
        return Response(body)

        if not integration.provider_id or integration.provider_id == '':
            return Response({
                'error': 'Please select a GA4 property first',
                'needs_property_selection': True,
            }, status=status.HTTP_400_BAD_REQUEST)

        credentials = get_credentials_from_integration(integration)
        if not credentials:
            return Response(
                {'error': 'No valid credentials found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = build('analyticsdata', 'v1beta', credentials=credentials)

        property_id = integration.provider_id
        if not property_id.startswith('properties/'):
            property_id = f'properties/{property_id}'

        # Run report with session source dimension. Filtering with the shared
        # AI_SOURCE_REGEX (matchType PARTIAL_REGEXP == GA4's "matches regex")
        # returns the exact same sessionSource rows the team's GA4 explore does.
        response = service.properties().runReport(
            property=property_id,
            body={
                'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                'metrics': [
                    {'name': 'sessions'},
                    {'name': 'totalUsers'},
                    {'name': 'screenPageViews'},
                    {'name': 'conversions'},
                    # purchaseRevenue == GA4's "Purchase revenue" column, so this
                    # filtered/live window reconciles with GA4 exactly like the
                    # cached snapshot does (see ga_insights_processor).
                    {'name': 'purchaseRevenue'},
                    {'name': 'bounceRate'},
                    {'name': 'averageSessionDuration'},
                    # GA4's "Session key event rate (purchase)" column — sessions
                    # that completed a purchase ÷ sessions. Event-scoped, so it's a
                    # clean 0 for lead-gen properties with no `purchase` key event
                    # and the real rate for e-commerce; reconciles with GA4 exactly.
                    # Returned as a fraction (0.013 = 1.3%).
                    {'name': 'sessionKeyEventRate:purchase'},
                ],
                'dimensions': [
                    {'name': 'sessionSource'},
                ],
                'dimensionFilter': {
                    'filter': {
                        'fieldName': 'sessionSource',
                        'stringFilter': {
                            'matchType': 'PARTIAL_REGEXP',
                            'value': AI_SOURCE_REGEX,
                            'caseSensitive': False,
                        }
                    }
                },
                'orderBys': [
                    {'metric': {'metricName': 'sessions'}, 'desc': True}
                ]
            }
        ).execute()

        # Parse and categorize by AI platform
        ai_traffic = parse_ai_referral_response(response)

        # GA4 reports revenue in the property's configured currency. Surface its
        # ISO code (e.g. INR, USD) so the dashboard renders the right symbol
        # instead of a hardcoded "$". GA4 returns it in the report metadata.
        report_metadata = response.get('metadata', {})
        currency_code = report_metadata.get('currencyCode') or 'USD'

        # Tell the dashboard whether GA4 sampled this response. Our Data API
        # numbers are normally UNSAMPLED (exact, and match GA4's Reports view);
        # only GA4 Explorations sample. Surfacing this lets the UI reassure the
        # client that a figure is exact vs. a GA4 estimate. See _extract_sampling.
        sampling = _extract_sampling_metadata(report_metadata)

        body = {
            'success': True,
            'ai_traffic': ai_traffic,
            'platform_breakdown': ai_traffic['platform_breakdown'],
            'totals': ai_traffic['totals'],
            'currency_code': currency_code,
            'sampling': sampling,
            'date_range': {'start': start_date, 'end': end_date, 'days': days},
        }
        cache.set(cache_key, {'body': body}, AI_REFERRAL_CACHE_TTL)
        return Response(body)

    except Integration.DoesNotExist:
        return Response(
            {'error': 'Google Analytics integration not found or not active'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error fetching AI referral data: {str(e)}")
        body = {'error': str(e)}
        # Negative-cache the failure briefly so a quota 429 doesn't trigger a
        # burst of further GA4 calls that all 429 and deepen the exhaustion.
        cache.set(cache_key, {'body': body, 'status': status.HTTP_500_INTERNAL_SERVER_ERROR}, AI_REFERRAL_ERROR_TTL)
        return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ai_referral_timeseries(request):
    """
    Daily AI-referred traffic (sessions + users) for a domain.

    Same GA4 ``sessionSource`` AI filter as :func:`get_ai_referral_data`, but
    dimensioned by DATE instead of source, so the dashboard can plot AI traffic
    over time and correlate it against the AI Visibility trend. Accepts
    ?days=N or explicit ?start_date=&end_date=. Returns the same
    ``{data: {daily, totals}}`` shape as :func:`get_ga_data` (each daily row is
    ``{date: 'YYYYMMDD', sessions, totalUsers}``) so the frontend reuses the
    existing GA parsing path.
    """
    domain_id = request.query_params.get('domain_id')
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    days_param = request.query_params.get('days')

    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Match get_ai_referral_data's window semantics: when no explicit range is
    # given, end YESTERDAY (GA4 treats today as an incomplete day) over `days`.
    days = None
    if not (start_date and end_date):
        try:
            days = int(days_param) if days_param else 28
        except (TypeError, ValueError):
            days = 28
        window_end = datetime.now().date() - timedelta(days=1)
        window_start = window_end - timedelta(days=days - 1)
        end_date = window_end.strftime('%Y-%m-%d')
        start_date = window_start.strftime('%Y-%m-%d')

    cache_key = _ai_referral_cache_key('ai_referral_ts', domain_id, start_date, end_date, days)
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached['body'], status=cached.get('status', status.HTTP_200_OK))

    try:
        integration = Integration.objects.get(
            domain_id=domain_id,
            type='google_analytics',
            status='active'
        )

        # Served from ga_ai_traffic_daily — see the note in get_ai_referral_data.
        _ensure_traffic_synced(domain_id, days)
        _start = datetime.strptime(start_date, '%Y-%m-%d').date()
        _end = datetime.strptime(end_date, '%Y-%m-%d').date()
        body = _build_ai_timeseries_body(domain_id, _start, _end, days)
        cache.set(cache_key, {'body': body}, AI_REFERRAL_CACHE_TTL)
        return Response(body)

        if not integration.provider_id or integration.provider_id == '':
            return Response({
                'error': 'Please select a GA4 property first',
                'needs_property_selection': True,
            }, status=status.HTTP_400_BAD_REQUEST)

        credentials = get_credentials_from_integration(integration)
        if not credentials:
            return Response(
                {'error': 'No valid credentials found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = build('analyticsdata', 'v1beta', credentials=credentials)

        property_id = integration.provider_id
        if not property_id.startswith('properties/'):
            property_id = f'properties/{property_id}'

        # Date-dimensioned report, filtered to AI sources with the SAME regex the
        # single-window AI-referral report uses, so daily totals reconcile with it.
        response = service.properties().runReport(
            property=property_id,
            body={
                'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                'metrics': [
                    {'name': 'sessions'},
                    {'name': 'totalUsers'},
                ],
                'dimensions': [
                    {'name': 'date'},
                ],
                'dimensionFilter': {
                    'filter': {
                        'fieldName': 'sessionSource',
                        'stringFilter': {
                            'matchType': 'PARTIAL_REGEXP',
                            'value': AI_SOURCE_REGEX,
                            'caseSensitive': False,
                        }
                    }
                },
                'orderBys': [
                    {'dimension': {'dimensionName': 'date'}}
                ]
            }
        ).execute()

        data = parse_ga_response(response)
        sampling = _extract_sampling_metadata(response.get('metadata', {}))

        body = {
            'success': True,
            'data': data,
            'date_range': {'start': start_date, 'end': end_date, 'days': days},
            'sampling': sampling,
        }
        cache.set(cache_key, {'body': body}, AI_REFERRAL_CACHE_TTL)
        return Response(body)

    except Integration.DoesNotExist:
        return Response(
            {'error': 'Google Analytics integration not found or not active'},
            status=status.HTTP_404_NOT_FOUND
        )
    except HttpError as e:
        logger.error(f"Google Analytics API error (AI timeseries): {e}")
        body = {'error': f'Google Analytics API error: {str(e)}'}
        cache.set(cache_key, {'body': body, 'status': status.HTTP_500_INTERNAL_SERVER_ERROR}, AI_REFERRAL_ERROR_TTL)
        return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Error fetching AI referral timeseries: {str(e)}")
        body = {'error': str(e)}
        cache.set(cache_key, {'body': body, 'status': status.HTTP_500_INTERNAL_SERVER_ERROR}, AI_REFERRAL_ERROR_TTL)
        return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def parse_ga_response(response):
    """Parse Google Analytics API response into a cleaner format."""
    rows = response.get('rows', [])
    metric_headers = [h['name'] for h in response.get('metricHeaders', [])]
    dimension_headers = [h['name'] for h in response.get('dimensionHeaders', [])]

    data = {
        'daily': [],
        'totals': {},
    }

    totals = {metric: 0 for metric in metric_headers}

    for row in rows:
        dimensions = {dimension_headers[i]: val['value'] for i, val in enumerate(row.get('dimensionValues', []))}
        metrics = {metric_headers[i]: float(val['value']) for i, val in enumerate(row.get('metricValues', []))}

        data['daily'].append({
            **dimensions,
            **metrics
        })

        for metric, value in metrics.items():
            totals[metric] += value

    data['totals'] = totals

    return data


def _f(values, idx, cast=float, default=0):
    """Safely read metricValues[idx] from a GA4 row, casting GA4's string numbers."""
    try:
        return cast(float(values[idx]['value']))
    except (IndexError, KeyError, TypeError, ValueError):
        return default


def _extract_sampling_metadata(report_metadata):
    """Read GA4's sampling state out of a runReport response's metadata.

    GA4 returns one SamplingMetadata per requested date range; a range is
    sampled when ``samplesReadCount < samplingSpaceSize`` (GA4 read only a
    subset of sessions and extrapolated). When the list is absent or empty the
    response is fully UNSAMPLED — i.e. exact, and reconciles with GA4's Reports
    view. (Only GA4's Explorations UI samples, and that estimate can't be
    reproduced through the Data API, so we report the unsampled truth and just
    flag whether GA4 itself would have sampled.)

    Returns ``{'is_sampled': bool, 'percent_sampled': float|None}`` where the
    percent is the share of sessions GA4 actually read (None when unsampled).
    """
    samplings = report_metadata.get('samplingMetadatas') or []
    is_sampled = False
    percent = None
    for s in samplings:
        try:
            read = int(s.get('samplesReadCount', 0))
            space = int(s.get('samplingSpaceSize', 0))
        except (TypeError, ValueError):
            continue
        if space > 0 and read < space:
            is_sampled = True
            percent = round((read / space) * 100, 1)
    return {'is_sampled': is_sampled, 'percent_sampled': percent}


def parse_ai_referral_response(response):
    """Parse an AI-referral GA4 response and aggregate by canonical platform.

    Platform classification uses the shared integrations.ai_platforms matcher so
    every variant GA4 counts (bare "perplexity", subdomains, Copilot, Meta AI,
    Mistral, …) folds into the same label the dashboard already uses.

    Returns both the legacy ``by_platform`` shape and a ``platform_breakdown``
    shape identical to GATrafficInsight.platform_breakdown, so the frontend can
    render a live window with the exact same code path as the cached snapshot.
    """
    rows = response.get('rows', [])

    by_platform = {}        # legacy shape: sessions/users/pageviews/sources
    platform_breakdown = {}  # dashboard shape: visits/conversions/revenue/...
    rate_weight = {}         # platform -> sessions, for weighted rate averages

    totals = {'visits': 0, 'conversions': 0, 'revenue': 0.0, 'users': 0, 'pageViews': 0}

    for row in rows:
        source = row.get('dimensionValues', [{}])[0].get('value', '')
        mv = row.get('metricValues', [])

        sessions = int(_f(mv, 0, int))
        users = int(_f(mv, 1, int))
        pageviews = int(_f(mv, 2, int))
        conversions = int(_f(mv, 3, int))
        revenue = _f(mv, 4, float)
        bounce_rate = _f(mv, 5, float)
        avg_duration = _f(mv, 6, float)
        # GA4 sessionKeyEventRate:purchase — a per-session rate (fraction).
        conv_rate = _f(mv, 7, float)

        platform_name = resolve_platform(source) or 'Other AI'

        if platform_name not in by_platform:
            by_platform[platform_name] = {'sessions': 0, 'users': 0, 'pageviews': 0, 'sources': []}
            platform_breakdown[platform_name] = {
                'visits': 0, 'conversions': 0, 'revenue': 0,
                'bounceRate': 0, 'avgDuration': 0, 'conversionRate': 0,
                'users': 0, 'pageViews': 0,
                # Raw GA4 sessionSource rows that roll up into this LLM, so the
                # dashboard can show clients exactly how each card reconciles
                # with GA4 (e.g. Perplexity = "perplexity" + "perplexity.ai").
                'sources': [],
            }
            rate_weight[platform_name] = 0

        bp = by_platform[platform_name]
        bp['sessions'] += sessions
        bp['users'] += users
        bp['pageviews'] += pageviews
        bp['sources'].append(source)

        pb = platform_breakdown[platform_name]
        pb['visits'] += sessions
        pb['sources'].append({'source': source, 'visits': sessions})
        pb['conversions'] += conversions
        pb['revenue'] += revenue
        pb['users'] += users
        pb['pageViews'] += pageviews
        # Rates are weighted by sessions and divided out after the loop. For
        # sessionKeyEventRate:purchase this weighted average is mathematically
        # exact (rate_i × sessions_i = purchasing sessions_i), so a multi-source
        # platform reconciles with GA4's combined rate.
        pb['bounceRate'] += bounce_rate * sessions
        pb['avgDuration'] += avg_duration * sessions
        pb['conversionRate'] += conv_rate * sessions
        rate_weight[platform_name] += sessions

        totals['visits'] += sessions
        totals['conversions'] += conversions
        totals['revenue'] += revenue
        totals['users'] += users
        totals['pageViews'] += pageviews

    for name, pb in platform_breakdown.items():
        weight = rate_weight.get(name, 0)
        if weight > 0:
            pb['bounceRate'] = pb['bounceRate'] / weight
            pb['avgDuration'] = pb['avgDuration'] / weight
            pb['conversionRate'] = pb['conversionRate'] / weight
        else:
            pb['bounceRate'] = 0
            pb['avgDuration'] = 0
            pb['conversionRate'] = 0
        # Largest contributing source first, for a readable reconciliation list.
        pb['sources'].sort(key=lambda s: s['visits'], reverse=True)

    return {
        'by_platform': by_platform,
        'platform_breakdown': platform_breakdown,
        'totals': totals,
    }


# ---------------------------------------------------------------------------
# DB-backed readers for AI-referred traffic.
#
# These endpoints used to call GA4 on every request and keep the answer only in
# a 15-minute cache, which meant the numbers existed nowhere durable, the
# traffic tabs 429'd on GA4's hourly quota under ordinary use, and disconnecting
# the integration erased the history. `ga_ai_traffic_daily` now holds it, filled
# by the nightly `sync_ai_traffic` command.
#
# Response shapes are unchanged — the frontend is untouched.
# ---------------------------------------------------------------------------

def _stored_ai_traffic_rows(domain_id, start_date, end_date):
    """Per-platform rows for the window, excluding the combined sentinel."""
    from .models import GAAITrafficDaily
    return GAAITrafficDaily.objects.filter(
        domain_id=domain_id,
        date__gte=start_date,
        date__lte=end_date,
    ).exclude(platform=GAAITrafficDaily.ALL_PLATFORMS)


def _ensure_traffic_synced(domain_id, days):
    """Backfill on first use so a newly connected property is not blank until
    the nightly job runs. Only ever fires when the domain has NO stored rows at
    all; steady state never touches GA4 from the request path."""
    from .models import GAAITrafficDaily
    if GAAITrafficDaily.objects.filter(domain_id=domain_id).exists():
        return
    try:
        from django.core.management import call_command
        call_command('sync_ai_traffic', domain_id=int(domain_id), days=max(int(days or 28), 90), verbosity=0)
    except Exception as exc:
        logger.warning("On-demand AI traffic sync failed for domain %s: %s", domain_id, exc)


def _build_ai_traffic_body(domain_id, start_date, end_date, days):
    """`get_ai_referral_data`'s body, assembled from stored rows."""
    from .models import GAAITrafficDaily

    totals = {'visits': 0, 'conversions': 0, 'revenue': 0.0, 'users': 0, 'pageViews': 0}
    platform_breakdown = {}
    by_platform = {}
    duration_weight = {}

    for r in _stored_ai_traffic_rows(domain_id, start_date, end_date):
        name = r.platform
        pb = platform_breakdown.setdefault(name, {
            'visits': 0, 'conversions': 0, 'revenue': 0,
            'bounceRate': 0, 'avgDuration': 0, 'conversionRate': 0,
            'users': 0, 'pageViews': 0,
        })
        bp = by_platform.setdefault(name, {'sessions': 0, 'users': 0, 'pageviews': 0, 'sources': []})

        pb['visits'] += r.sessions
        pb['users'] += r.users
        pb['pageViews'] += r.page_views
        pb['conversions'] += r.conversions
        bp['sessions'] += r.sessions
        bp['users'] += r.users
        bp['pageviews'] += r.page_views
        # Session-weighted, so the window's average duration is a real mean and
        # not an average of daily averages.
        duration_weight[name] = duration_weight.get(name, 0.0) + float(r.avg_duration or 0) * r.sessions

        totals['visits'] += r.sessions
        totals['users'] += r.users
        totals['pageViews'] += r.page_views
        totals['conversions'] += r.conversions

    for name, pb in platform_breakdown.items():
        if pb['visits']:
            pb['avgDuration'] = round(duration_weight.get(name, 0.0) / pb['visits'], 2)
            pb['conversionRate'] = round(pb['conversions'] / pb['visits'], 4)

    synced_at = (GAAITrafficDaily.objects
                 .filter(domain_id=domain_id)
                 .order_by('-synced_at')
                 .values_list('synced_at', flat=True)
                 .first())

    return {
        'success': True,
        'ai_traffic': {'by_platform': by_platform, 'platform_breakdown': platform_breakdown, 'totals': totals},
        'platform_breakdown': platform_breakdown,
        'totals': totals,
        'currency_code': 'USD',
        # Stored rows come from the Data API, which is unsampled.
        'sampling': {'is_sampled': False},
        'date_range': {'start': str(start_date), 'end': str(end_date), 'days': days},
        'source': 'db',
        'synced_at': synced_at.isoformat() if synced_at else None,
    }


def _build_ai_timeseries_body(domain_id, start_date, end_date, days):
    """`get_ai_referral_timeseries`'s body, assembled from the combined rows."""
    from .models import GAAITrafficDaily

    rows = GAAITrafficDaily.objects.filter(
        domain_id=domain_id,
        date__gte=start_date,
        date__lte=end_date,
        platform=GAAITrafficDaily.ALL_PLATFORMS,
    ).order_by('date')

    daily = [{
        'date': r.date.strftime('%Y%m%d'),
        'sessions': r.sessions,
        'totalUsers': r.users,
    } for r in rows]

    return {
        'success': True,
        'data': {
            'daily': daily,
            'totals': {
                'sessions': sum(d['sessions'] for d in daily),
                'totalUsers': sum(d['totalUsers'] for d in daily),
            },
        },
        'date_range': {'start': str(start_date), 'end': str(end_date), 'days': days},
        'sampling': {'is_sampled': False},
        'source': 'db',
    }
