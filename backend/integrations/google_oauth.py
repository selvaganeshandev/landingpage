"""
Google OAuth 2.0 integration for Google Analytics and Search Console.
"""
import json
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import Integration
from domains.models import Domain, DomainAccess

logger = logging.getLogger(__name__)

# Google OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/analytics.readonly',  # GA4 Data API
    'https://www.googleapis.com/auth/webmasters.readonly',  # Search Console
]

# Frontend URL for redirect after OAuth
FRONTEND_URL = 'http://localhost:8080'


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
    integration_type = request.query_params.get('integration_type', 'google_analytics')

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

    # Create state parameter with domain_id, integration_type, and user_id
    state_data = {
        'domain_id': domain_id,
        'integration_type': integration_type,
        'user_id': request.user.id,
    }
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

    if error:
        logger.error(f"Google OAuth error: {error}")
        return redirect(f'{FRONTEND_URL}/organization-settings?error=google_auth_denied')

    if not code or not state:
        return redirect(f'{FRONTEND_URL}/organization-settings?error=missing_params')

    try:
        # Parse state to get domain_id and integration_type
        state_data = json.loads(state)
        domain_id = state_data.get('domain_id')
        integration_type = state_data.get('integration_type', 'google_analytics')
        user_id = state_data.get('user_id')

        if not domain_id or not user_id:
            return redirect(f'{FRONTEND_URL}/organization-settings?error=invalid_state')

        # Exchange code for tokens
        flow = create_oauth_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Get the domain
        try:
            domain = Domain.objects.get(pk=domain_id)
        except Domain.DoesNotExist:
            return redirect(f'{FRONTEND_URL}/organization-settings?error=domain_not_found')

        # Get the user
        from authentication.models import Account
        try:
            user = Account.objects.get(pk=user_id)
        except Account.DoesNotExist:
            return redirect(f'{FRONTEND_URL}/organization-settings?error=user_not_found')

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

        # Create or update integration
        integration, created = Integration.objects.update_or_create(
            domain=domain,
            type=integration_type,
            defaults={
                'provider_id': provider_id,
                'credentials': credentials_data,
                'status': integration_status,
                'last_sync_at': timezone.now(),
                'error_message': credentials_data.get('error_message'),
                'created_by': user,
            }
        )

        # Redirect back to frontend with success
        redirect_url = f'{FRONTEND_URL}/organization-settings/domains/{domain_id}?tab=integrations&success=google_connected&type={integration_type}'
        return redirect(redirect_url)

    except json.JSONDecodeError:
        return redirect(f'{FRONTEND_URL}/organization-settings?error=invalid_state')
    except Exception as e:
        logger.error(f"Error in Google OAuth callback: {str(e)}")
        return redirect(f'{FRONTEND_URL}/organization-settings?error=oauth_failed')


def get_credentials_from_integration(integration):
    """Convert stored credentials back to Google Credentials object."""
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
    )

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

        # Create INIT record for processing
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

        # Create INIT record for processing
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ai_referral_data(request):
    """
    Fetch traffic data specifically from AI platforms.
    Tracks referrals from: ChatGPT, Claude, Gemini, Perplexity, Grok
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

        # AI platform domains to track
        ai_platforms = [
            'chat.openai.com',
            'chatgpt.com',
            'claude.ai',
            'gemini.google.com',
            'bard.google.com',
            'perplexity.ai',
            'grok.x.ai',
            'you.com',
            'poe.com',
        ]

        # Run report with session source dimension
        response = service.properties().runReport(
            property=property_id,
            body={
                'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                'metrics': [
                    {'name': 'sessions'},
                    {'name': 'totalUsers'},
                    {'name': 'screenPageViews'},
                ],
                'dimensions': [
                    {'name': 'sessionSource'},
                ],
                'dimensionFilter': {
                    'orGroup': {
                        'expressions': [
                            {
                                'filter': {
                                    'fieldName': 'sessionSource',
                                    'stringFilter': {
                                        'matchType': 'CONTAINS',
                                        'value': platform,
                                        'caseSensitive': False,
                                    }
                                }
                            }
                            for platform in ai_platforms
                        ]
                    }
                },
                'orderBys': [
                    {'metric': {'metricName': 'sessions'}, 'desc': True}
                ]
            }
        ).execute()

        # Parse and categorize by AI platform
        ai_traffic = parse_ai_referral_response(response, ai_platforms)

        return Response({
            'success': True,
            'ai_traffic': ai_traffic,
            'date_range': {'start': start_date, 'end': end_date},
        })

    except Integration.DoesNotExist:
        return Response(
            {'error': 'Google Analytics integration not found or not active'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error fetching AI referral data: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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


def parse_ai_referral_response(response, ai_platforms):
    """Parse AI referral response and categorize by platform."""
    rows = response.get('rows', [])

    # Platform name mapping
    platform_names = {
        'chat.openai.com': 'ChatGPT',
        'chatgpt.com': 'ChatGPT',
        'claude.ai': 'Claude',
        'gemini.google.com': 'Google Gemini',
        'bard.google.com': 'Google Gemini',
        'perplexity.ai': 'Perplexity',
        'grok.x.ai': 'Grok',
        'you.com': 'You.com',
        'poe.com': 'Poe',
    }

    # Aggregate by platform
    platform_data = {}
    total_sessions = 0
    total_users = 0
    total_pageviews = 0

    for row in rows:
        source = row['dimensionValues'][0]['value']
        sessions = int(row['metricValues'][0]['value'])
        users = int(row['metricValues'][1]['value'])
        pageviews = int(row['metricValues'][2]['value'])

        # Find which platform this source belongs to
        platform_name = 'Other AI'
        for domain, name in platform_names.items():
            if domain in source.lower():
                platform_name = name
                break

        if platform_name not in platform_data:
            platform_data[platform_name] = {
                'sessions': 0,
                'users': 0,
                'pageviews': 0,
                'sources': []
            }

        platform_data[platform_name]['sessions'] += sessions
        platform_data[platform_name]['users'] += users
        platform_data[platform_name]['pageviews'] += pageviews
        platform_data[platform_name]['sources'].append(source)

        total_sessions += sessions
        total_users += users
        total_pageviews += pageviews

    return {
        'by_platform': platform_data,
        'totals': {
            'sessions': total_sessions,
            'users': total_users,
            'pageviews': total_pageviews,
        }
    }
