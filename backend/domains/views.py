from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction, connection
from django.db import IntegrityError
from django.db.utils import ProgrammingError
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Domain, DomainAccess, InternalLinkMap, ReferenceDocument, BrandLink, BrandLinkChunk
from authentication.models import UserPermission
from .serializers import (
    DomainMinimalSerializer, DomainSerializer, DomainDetailSerializer,
    DomainAccessSerializer, DomainAccessCreateSerializer,
    InternalLinkMapSerializer, InternalLinkMapCreateSerializer,
    ReferenceDocumentSerializer,
    BrandLinkSerializer
)
from authentication.serializers import AccountSerializer
from authentication.models import Account
from keywords.models import SecondaryKeyword
import json
import logging

logger = logging.getLogger(__name__)


def get_openai_client():
    """Return OpenAI client if configured in Django settings; else raise."""
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        raise Exception("OpenAI API key not configured")
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key, timeout=60)
    except Exception as e:
        raise Exception(f"Failed to initialize OpenAI client: {e}")


def get_google_genai_client():
    """Return Google GenerativeAI client if configured in Django settings; else raise."""
    api_key = getattr(settings, "GOOGLE_GEMINI_API_KEY", None)
    if not api_key:
        raise Exception("Google GenAI API key not configured")
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key, transport="rest")
        return genai
    except Exception as e:
        raise Exception(f"Failed to initialize Google GenAI client: {e}")


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def domain_list(request):
    """List all domains for the organization or create a new one"""
    if request.method == 'GET':
        # Filter domains by organization and user access
        if request.user.role in ('super_admin', 'admin'):
            # Super admins and admins see all org domains
            domains = Domain.objects.filter(organisation=request.user.organisation)
        else:
            # Regular users can only see domains they have explicit access to
            domain_ids = DomainAccess.objects.filter(
                user=request.user,
                domain__organisation=request.user.organisation
            ).values_list('domain_id', flat=True)
            domains = Domain.objects.filter(id__in=domain_ids)

        # Optimize queries: select_related for FK, prefetch_related for reverse FK
        if request.query_params.get('fields') == 'minimal':
            domains = domains.only('id', 'name', 'url')
        else:
            domains = domains.select_related('organisation').prefetch_related('health_checks')

        # Search support
        search = request.query_params.get('search', '').strip()
        if search:
            domains = domains.filter(
                Q(name__icontains=search) | Q(url__icontains=search)
            )

        # Pagination support
        page = request.query_params.get('page')
        page_size = request.query_params.get('page_size')

        total_count = domains.count()

        if page and page_size:
            try:
                page = int(page)
                page_size = int(page_size)
                offset = (page - 1) * page_size
                domains = domains[offset:offset + page_size]
            except (ValueError, TypeError):
                pass

        # Use minimal serializer for lightweight requests (popups, dropdowns)
        if request.query_params.get('fields') == 'minimal':
            serializer = DomainMinimalSerializer(domains, many=True)
        else:
            serializer = DomainSerializer(domains, many=True)
        return Response({
            'domains': serializer.data,
            'total_count': total_count,
        })
    
    elif request.method == 'POST':
        # Only admins can create domains
        if request.user.role not in ['admin', 'super_admin']:
            return Response(
                {'error': 'Only organization administrators can add domains'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Add organization to the data
        data = request.data.copy()
        data['organisation'] = request.user.organisation.id

        # Convert country code to country name
        country_code = data.get('country', 'us')
        country_map = {
            'us': 'United States', 'gb': 'United Kingdom', 'ca': 'Canada',
            'au': 'Australia', 'de': 'Germany', 'fr': 'France', 'es': 'Spain',
            'it': 'Italy', 'jp': 'Japan', 'in': 'India', 'br': 'Brazil',
            'mx': 'Mexico', 'nl': 'Netherlands', 'se': 'Sweden', 'no': 'Norway',
            'dk': 'Denmark', 'fi': 'Finland', 'pl': 'Poland', 'be': 'Belgium',
            'at': 'Austria', 'ch': 'Switzerland', 'ie': 'Ireland',
            'nz': 'New Zealand', 'sg': 'Singapore'
        }
        data['country'] = country_map.get(country_code.lower(), 'United States')

        # Normalize domain and extract brand name
        raw_input = data.get('name') or data.get('url') or ''
        if isinstance(raw_input, str):
            normalized = raw_input.strip().lower()
            # Remove scheme
            if normalized.startswith('http://'):
                normalized = normalized[len('http://'):]
            elif normalized.startswith('https://'):
                normalized = normalized[len('https://'):]
            # Strip leading www.
            if normalized.startswith('www.'):
                normalized = normalized[4:]
            # Keep only host part before path or query
            for sep in ['/', '?', '#']:
                if sep in normalized:
                    normalized = normalized.split(sep, 1)[0]
            # Remove port if present
            if ':' in normalized:
                normalized = normalized.split(':', 1)[0]

            # Extract brand name from domain (e.g., "airbnb.com" -> "Airbnb")
            # Remove common TLDs and format as title case
            brand_name = normalized
            for tld in ['.com', '.io', '.org', '.net', '.co', '.ai', '.app', '.dev', '.in', '.uk', '.co.uk', '.co.in']:
                if brand_name.endswith(tld):
                    brand_name = brand_name[:-len(tld)]
                    break
            # Replace separators with spaces and title case
            brand_name = brand_name.replace('-', ' ').replace('_', ' ').title()

            # Use just the brand name (without country)
            data['name'] = brand_name

            # Store the normalized domain as URL if not already provided
            if not data.get('url'):
                data['url'] = f"https://{normalized}"
        
        # Validate keywords are provided (mandatory)
        keywords_str = data.get('keywords', '')
        if not keywords_str or not keywords_str.strip():
            return Response(
                {'error': 'At least one keyword is required. Keywords are mandatory for domain creation.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse keywords: split by comma, normalize to lowercase, trim whitespace
        keywords_list = [
            k.strip().lower() 
            for k in keywords_str.split(',') 
            if k.strip() and len(k.strip()) <= 255
        ]
        
        if not keywords_list:
            return Response(
                {'error': 'At least one valid keyword is required. Keywords must be non-empty and less than 255 characters.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = DomainSerializer(data=data)
        if serializer.is_valid():
            # Use transaction to ensure domain is created successfully
            try:
                with transaction.atomic():
                    domain = serializer.save()

                    # NOTE: Keywords are NOT automatically created here anymore.
                    # The frontend handles keyword creation separately via:
                    # - /keywords/bulk-create/ for selected (primary) keywords
                    # - /keywords/secondary/bulk-create/ for unselected keywords
                    # This allows proper separation between primary and secondary keywords.

                    # The keywords field in the domain stores the comma-separated list
                    # for reference, but actual Keyword objects are created by the frontend.

                    # Auto-grant DomainAccess to all existing org members
                    org_members = Account.objects.filter(
                        organisation=request.user.organisation,
                        is_active=True
                    )
                    for member in org_members:
                        DomainAccess.objects.get_or_create(
                            user=member,
                            domain=domain,
                            defaults={'granted_by': request.user}
                        )

                    return Response({
                        'message': 'Domain added successfully',
                        'domain': DomainSerializer(domain).data,
                    }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {'error': f'Failed to create domain: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def domain_detail(request, pk):
    """Retrieve, update or delete a domain"""
    try:
        if request.user.role in ('super_admin', 'admin'):
            domain = Domain.objects.get(pk=pk, organisation=request.user.organisation)
        else:
            # Check if user has access to this domain
            domain_access = DomainAccess.objects.get(
                user=request.user,
                domain_id=pk,
                domain__organisation=request.user.organisation
            )
            domain = domain_access.domain
    except (Domain.DoesNotExist, DomainAccess.DoesNotExist):
        return Response(
            {'error': 'Domain not found or you do not have access to this domain'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = DomainDetailSerializer(domain)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Only admins can update domains
        if request.user.role not in ['admin', 'super_admin']:
            return Response(
                {'error': 'Only organization administrators can update domains'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DomainSerializer(domain, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Domain updated successfully',
                'domain': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only admins can delete domains
        if request.user.role not in ['admin', 'super_admin']:
            return Response(
                {'error': 'Only organization administrators can delete domains'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Explicitly delete SecondaryKeyword records first to avoid SQL cascade errors
        # Handle case where table might not exist (migrations not run)
        try:
            with transaction.atomic():
                domain_id = domain.id
                
                # Try to delete secondary keywords if table exists
                # This prevents SQL errors from cascade deletion
                # First check if the table exists in the database
                table_exists = False
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_schema = 'public' 
                                AND table_name = 'secondary_keywords'
                            );
                        """)
                        table_exists = cursor.fetchone()[0]
                except Exception as check_error:
                    logger.warning(f"Could not check if secondary_keywords table exists: {str(check_error)}")
                    # Try to proceed with deletion anyway
                    table_exists = True
                
                if table_exists:
                    try:
                        deleted_count = SecondaryKeyword.objects.filter(domain_id=domain_id).delete()[0]
                        if deleted_count > 0:
                            logger.info(f"Deleted {deleted_count} secondary keywords for domain {domain_id}")
                    except (ProgrammingError, Exception) as secondary_keyword_error:
                        # Table might have been deleted between check and deletion
                        error_msg = str(secondary_keyword_error).lower()
                        if 'does not exist' in error_msg or 'relation' in error_msg:
                            logger.info(f"secondary_keywords table does not exist, skipping deletion")
                        else:
                            # Re-raise if it's a different error
                            logger.warning(f"Could not delete secondary keywords for domain {domain_id}: {str(secondary_keyword_error)}")
                            raise
                else:
                    logger.info(f"secondary_keywords table does not exist, skipping deletion")
                
                # Now delete the domain (cascade will handle other related records)
                # If table doesn't exist, Django's cascade might still try to delete from it
                # So we catch ProgrammingError related to secondary_keywords
                try:
                    domain.delete()
                except ProgrammingError as cascade_error:
                    error_msg = str(cascade_error).lower()
                    if 'secondary_keywords' in error_msg and ('does not exist' in error_msg or 'relation' in error_msg):
                        # Table doesn't exist - this is a migration issue
                        # Delete domain using raw SQL to bypass ORM cascade
                        logger.warning(f"Cascade deletion failed due to missing secondary_keywords table, using raw SQL deletion")
                        try:
                            with connection.cursor() as cursor:
                                cursor.execute("DELETE FROM domains WHERE id = %s", [domain_id])
                            logger.info(f"Domain {domain_id} deleted successfully using raw SQL")
                        except Exception as raw_sql_error:
                            logger.error(f"Raw SQL deletion also failed: {str(raw_sql_error)}")
                            raise Exception(
                                "Cannot delete domain: secondary_keywords table is missing. "
                                "Please run migrations: python manage.py migrate keywords"
                            )
                    else:
                        # Different ProgrammingError - re-raise
                        raise
                
            return Response({
                'message': 'Domain deleted successfully'
            })
        except Exception as e:
            logger.error(f"Error deleting domain {domain.id}: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Error deleting domain: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def domain_keywords(request, pk):
    """Get all keywords for a domain"""
    try:
        if request.user.role in ('super_admin', 'admin'):
            domain = Domain.objects.get(pk=pk, organisation=request.user.organisation)
        else:
            domain_access = DomainAccess.objects.get(
                user=request.user,
                domain_id=pk,
                domain__organisation=request.user.organisation
            )
            domain = domain_access.domain
    except (Domain.DoesNotExist, DomainAccess.DoesNotExist):
        return Response(
            {'error': 'Domain not found or you do not have access to this domain'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    keywords = domain.keywords.all()
    from keywords.serializers import KeywordSerializer
    serializer = KeywordSerializer(keywords, many=True)
    return Response(serializer.data)


# Domain Access Management
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def domain_access_list(request, domain_id):
    """List or grant domain access (no access levels)."""
    is_admin = request.user.role in ['admin', 'super_admin']
    has_team_mgmt = UserPermission.objects.filter(user=request.user, module='team_management').exists()
    if not is_admin and not has_team_mgmt:
        return Response({'error': 'Only organization administrators can manage domain access'}, status=status.HTTP_403_FORBIDDEN)
    try:
        domain = Domain.objects.get(id=domain_id, organisation=request.user.organisation)
    except Domain.DoesNotExist:
        return Response({'error': 'Domain not found or not in your organization'}, status=status.HTTP_404_NOT_FOUND)
    # Team members can only manage access for domains they themselves have access to
    if not is_admin:
        if not DomainAccess.objects.filter(user=request.user, domain=domain).exists():
            return Response({'error': 'You do not have access to this domain'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        access_list = DomainAccess.objects.filter(domain=domain)
        return Response({'access_list': DomainAccessSerializer(access_list, many=True).data})

    serializer = DomainAccessCreateSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Validate target user
    user_id = serializer.validated_data['user_id']
    try:
        user = Account.objects.get(id=user_id)
        if user.organisation != request.user.organisation:
            return Response({'error': 'User must be in the same organization'}, status=status.HTTP_400_BAD_REQUEST)
    except Account.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)

    # Grant access idempotently to avoid unique constraint violation
    access, created = DomainAccess.objects.get_or_create(
        domain=domain,
        user=user,
        defaults={'granted_by': request.user}
    )
    if not created:
        return Response({'message': 'Access already exists', 'access': DomainAccessSerializer(access).data}, status=status.HTTP_200_OK)

    return Response({'message': 'Access granted successfully', 'access': DomainAccessSerializer(access).data}, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def domain_access_detail(request, domain_id, user_id):
    is_admin = request.user.role in ['admin', 'super_admin']
    has_team_mgmt = UserPermission.objects.filter(user=request.user, module='team_management').exists()
    if not is_admin and not has_team_mgmt:
        return Response({'error': 'Only organization administrators can manage domain access'}, status=status.HTTP_403_FORBIDDEN)
    # Team members can only manage access for domains they themselves have access to
    if not is_admin:
        if not DomainAccess.objects.filter(user=request.user, domain_id=domain_id).exists():
            return Response({'error': 'You do not have access to this domain'}, status=status.HTTP_403_FORBIDDEN)
    try:
        domain = Domain.objects.get(id=domain_id, organisation=request.user.organisation)
        access = DomainAccess.objects.get(domain=domain, user_id=user_id)
    except Domain.DoesNotExist:
        return Response({'error': 'Domain not found or not in your organization'}, status=status.HTTP_404_NOT_FOUND)
    except DomainAccess.DoesNotExist:
        return Response({'error': 'User does not have access to this domain'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        # Nothing to update; return current
        return Response({'access': DomainAccessSerializer(access).data})

    access.delete()
    return Response({'message': 'Access revoked successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_domain_access_list(request, user_id):
    """Get all domain access for a specific user in one call (optimization)."""
    is_admin = request.user.role in ['admin', 'super_admin']
    has_team_mgmt = UserPermission.objects.filter(user=request.user, module='team_management').exists()
    if not is_admin and not has_team_mgmt:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    access_list = DomainAccess.objects.filter(
        user_id=user_id,
        domain__organisation=request.user.organisation
    ).select_related('domain')
    access_data = {a.domain_id: DomainAccessSerializer(a).data for a in access_list}
    return Response({'access_map': access_data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_users_for_domain(request, domain_id):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organization administrators can view available users'}, status=status.HTTP_403_FORBIDDEN)
    try:
        domain = Domain.objects.get(id=domain_id, organisation=request.user.organisation)
    except Domain.DoesNotExist:
        return Response({'error': 'Domain not found or not in your organization'}, status=status.HTTP_404_NOT_FOUND)

    users_with_access = DomainAccess.objects.filter(domain=domain).values_list('user_id', flat=True)
    available = request.user.organisation.accounts.exclude(id__in=users_with_access)
    data = [{
        'id': u.id,
        'email': u.email,
        'first_name': u.first_name,
        'last_name': u.last_name,
        'role': u.role,
    } for u in available]
    return Response({'available_users': data})


    # Domain Access Management views removed


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def fetch_brand_info(request):
    """
    Fetch brand information from ChatGPT based on domain name and URL.
    Returns: short_description, target_audience, brand_values, key_competitors,
             tone_of_voice, content_style, key_messages, topics_to_avoid
    """
    domain_name = request.data.get('domain_name', '').strip()
    domain_url = request.data.get('domain_url', '').strip()

    if not domain_name and not domain_url:
        return Response(
            {'error': 'Either domain_name or domain_url is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Use domain_url if provided, otherwise construct from domain_name
    website = domain_url if domain_url else f"https://{domain_name}"
    brand_name = domain_name.replace('.com', '').replace('.io', '').replace('.org', '').replace('.net', '').replace('-', ' ').replace('_', ' ').title()

    try:
        client = get_openai_client()

        prompt = f"""Analyze the brand/website "{brand_name}" ({website}) and provide the following information in JSON format.
If you don't have specific information about this brand, make reasonable inferences based on the domain name and common patterns for similar businesses.

Return ONLY a valid JSON object with these fields:
{{
    "short_description": "A brief 1-2 sentence description of what this brand/company does",
    "target_audience": "Description of the primary target audience demographics, interests, and needs",
    "brand_values": "Core values and principles the brand likely stands for (as a comma-separated list)",
    "key_competitors": "List of 3-5 likely competitors in the same space (as a comma-separated list)",
    "tone_of_voice": "Recommended tone of voice for content (e.g., professional, friendly, authoritative)",
    "content_style": "Recommended content style guidelines (e.g., concise, detailed, technical)",
    "key_messages": "Key messages or themes the brand should emphasize",
    "topics_to_avoid": "Topics or themes the brand should avoid in content"
}}

Provide helpful, realistic information that would be useful for brand monitoring and content creation."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a brand analyst expert. Analyze brands and provide structured information about them. Always respond with valid JSON only, no additional text."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        result_text = response.choices[0].message.content.strip()

        # Try to parse the JSON response
        try:
            # Remove markdown code blocks if present
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            brand_info = json.loads(result_text)

            return Response({
                'success': True,
                'brand_info': {
                    'short_description': brand_info.get('short_description', ''),
                    'target_audience': brand_info.get('target_audience', ''),
                    'brand_values': brand_info.get('brand_values', ''),
                    'key_competitors': brand_info.get('key_competitors', ''),
                    'tone_of_voice': brand_info.get('tone_of_voice', ''),
                    'content_style': brand_info.get('content_style', ''),
                    'key_messages': brand_info.get('key_messages', ''),
                    'topics_to_avoid': brand_info.get('topics_to_avoid', ''),
                }
            })
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ChatGPT response as JSON: {result_text}")
            return Response({
                'success': False,
                'error': 'Failed to parse AI response',
                'raw_response': result_text
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"Error fetching brand info from ChatGPT: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def fetch_brand_niches(request):
    """
    Fetch brand niches/categories using Google GenAI based on domain name and brand name.
    Returns: A list of relevant industry niches/categories for the brand
    """
    domain_name = request.data.get('domain_name', '').strip()
    brand_name = request.data.get('brand_name', '').strip()

    if not domain_name and not brand_name:
        return Response(
            {'error': 'Either domain_name or brand_name is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Use brand_name if provided, otherwise extract from domain_name
    if not brand_name:
        brand_name = domain_name.replace('.com', '').replace('.io', '').replace('.org', '').replace('.net', '').replace('-', ' ').replace('_', ' ').title()

    try:
        genai = get_google_genai_client()
        model = genai.GenerativeModel('gemini-2.0-flash')

        prompt = f"""Analyze the brand "{brand_name}" (website: {domain_name}) and suggest relevant industry niches or categories.

Return ONLY a JSON array of 5-8 specific industry niches/categories that best describe this brand's market positioning. Each niche should be:
- Specific and descriptive (e.g., "Enterprise Cloud Security Solutions" not just "Security")
- Industry-relevant
- Useful for market positioning and competitive analysis

Example format:
["Enterprise SaaS", "Cloud Infrastructure", "DevOps Tools", "IT Security", "Business Intelligence"]

Provide the response as a valid JSON array only, no additional text."""

        used_provider = 'gemini'
        try:
            response = model.generate_content(prompt)
            result_text = response.text.strip()
        except Exception as gemini_err:
            err_str = str(gemini_err)
            # Fall back to OpenAI ONLY for quota/429 errors. Other failures bubble up.
            if '429' in err_str or 'quota' in err_str.lower() or 'spend cap' in err_str.lower():
                logger.warning(f"Gemini quota/429 hit, falling back to OpenAI: {err_str}")
                used_provider = 'openai'
                openai_client = get_openai_client()
                openai_response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert brand/industry analyst. Respond with a JSON array only — no markdown, no commentary."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                    max_tokens=500,
                )
                result_text = openai_response.choices[0].message.content.strip()
            else:
                raise

        logger.info(f"brand_niches served by: {used_provider}")

        # Try to parse the JSON response
        try:
            # Remove markdown code blocks if present
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            niches = json.loads(result_text)

            # Validate it's a list
            if not isinstance(niches, list):
                raise ValueError("Response is not a list")

            # Filter to ensure all items are strings and limit to 10
            niches = [str(n).strip() for n in niches if n][:10]

            return Response({
                'success': True,
                'niches': niches
            })
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Google GenAI response as JSON: {result_text}")
            return Response({
                'success': False,
                'error': 'Failed to parse AI response',
                'raw_response': result_text
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"Error fetching brand niches from Google GenAI: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_semantic_keywords(request):
    """
    Generate semantic keywords using Google GenAI based on domain info.
    Returns: Top 100 keywords with semantic metadata
    """
    domain_name = request.data.get('domain_name', '').strip()
    brand_name = request.data.get('brand_name', '').strip()
    country = request.data.get('country', 'United States')
    niches = request.data.get('niches', [])
    approx_keywords = request.data.get('approx_keywords', 100)

    if not domain_name or not brand_name:
        return Response(
            {'error': 'domain_name and brand_name are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        genai = get_google_genai_client()
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Build niche description
        niche_text = ", ".join(niches) if niches else "general business"

        # Limit keywords to prevent response truncation
        max_keywords = min(approx_keywords, 50)

        # Build the prompt for semantic keyword generation
        prompt = f"""You are an expert SEO keyword researcher. Generate a comprehensive keyword universe for:

**Website:** {domain_name}
**Brand Name:** {brand_name}
**Country:** {country}
**Industry Niches:** {niche_text}
**Number of Keywords:** EXACTLY {max_keywords} unique, relevant keywords

Generate keywords that cover:
- Brand-related queries
- Product/service queries
- Informational queries
- Commercial/transactional queries
- Location-based queries (for {country})

For each keyword, provide:
1. **keyword**: The actual keyword phrase
2. **volume_level**: Estimated search volume (very-low, low, medium, high, very-high)
3. **intent**: Search intent type (informational, navigational, transactional, commercial)
4. **entity**: Main subject/noun of the keyword
5. **attribute**: Characteristic being queried (if applicable)
6. **variable**: Modifier/qualifier (if applicable)
7. **source**: Always set to "ai-generated"
8. **topic**: Main topic/category
9. **cluster_id**: Group identifier for related keywords

Return ONLY a valid JSON object with this structure (no markdown, no commentary):
{{
  "project": {{
    "country": "{country}",
    "language": "en",
    "website": "{domain_name}",
    "niche": "{niche_text}",
    "approx_keywords_requested": {max_keywords}
  }},
  "keywords": [
    {{
      "keyword": "example keyword",
      "volume_level": "medium",
      "intent": "informational",
      "entity": "product",
      "attribute": "price",
      "variable": "cheap",
      "source": "ai-generated",
      "topic": "pricing",
      "cluster_id": "cluster_1"
    }}
  ]
}}"""

        used_provider = 'gemini'
        try:
            # Bounded timeout so a quota/429 error surfaces in ~30s instead of
            # letting google.api_core silently exponential-back-off retry for
            # ~60s before raising. 30s (vs the old 15s) gives large keyword sets
            # — e.g. 50 keywords × 9 fields — room to finish on Gemini before we
            # fall back; combined with the 180s OpenAI cap it stays under the
            # frontend's 5-min window.
            response = model.generate_content(
                prompt,
                request_options={'timeout': 30},
            )
            result_text = response.text.strip()
        except Exception as gemini_err:
            err_str = str(gemini_err)
            err_lower = err_str.lower()
            # Fall back to OpenAI for quota/429 AND for transient errors (read
            # timeout, deadline exceeded, 5xx, connection drops). Previously only
            # 429/quota fell back, so a slow Gemini response (ReadTimeout on
            # generativelanguage.googleapis.com) failed outright instead of
            # retrying on OpenAI. Genuine bad-request/safety errors still bubble up.
            is_quota = '429' in err_str or 'quota' in err_lower or 'spend cap' in err_lower
            is_transient = any(s in err_lower for s in (
                'timed out', 'timeout', 'deadline', 'connection', 'connectionpool',
                'unavailable', '503', '500', '502', '504',
            ))
            if is_quota or is_transient:
                reason = 'quota/429' if is_quota else 'timeout/transient error'
                logger.warning(f"Gemini {reason}, falling back to OpenAI: {err_str}")
                used_provider = 'openai'
                openai_client = get_openai_client()
                openai_response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert SEO keyword researcher. Respond with valid JSON only — no markdown, no commentary."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                    # 50 keywords × 9 fields ≈ 7-9k tokens; 8000 is enough and
                    # cuts ~20-40s off gpt-4o-mini's generation time vs 16000.
                    max_tokens=8000,
                    response_format={"type": "json_object"},
                    # Hard cap so a stalled OpenAI request can't hold the
                    # connection beyond the frontend's 5-min window.
                    timeout=180,
                )
                result_text = openai_response.choices[0].message.content.strip()
            else:
                raise

        logger.info(f"semantic_keywords served by: {used_provider}")

        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            # Try to find and extract just the JSON content
            if not result_text.startswith('{'):
                # Find the first { and last }
                start = result_text.find('{')
                if start != -1:
                    result_text = result_text[start:]

            data = json.loads(result_text)

            # Validate structure
            if 'keywords' not in data or not isinstance(data['keywords'], list):
                raise ValueError("Invalid response structure")

            keywords = data['keywords']  # Use all returned keywords

            return Response({
                'success': True,
                'project': data.get('project', {}),
                'keywords': keywords,
                'total_keywords': len(keywords)
            })

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse semantic keywords response: {str(e)}")
            logger.error(f"Response length: {len(result_text)}")
            logger.error(f"Response preview: {result_text[:1000]}")
            return Response({
                'success': False,
                'error': f'Failed to parse AI response: {str(e)}',
                'raw_response': result_text[:500]
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"Error generating semantic keywords: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _fetch_pagespeed_data(url, strategy='mobile'):
    """
    Call Google PageSpeed Insights API.
    Returns dict with score, CWV metrics, speed_index, or None on failure.
    """
    import requests as req
    api_key = getattr(settings, 'GOOGLE_PAGESPEED_API_KEY', None)
    if not api_key:
        logger.warning("GOOGLE_PAGESPEED_API_KEY not configured")
        return None

    psi_url = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
    params = {
        'url': url,
        'strategy': strategy,
        'key': api_key,
        'category': 'performance'
    }
    try:
        resp = req.get(psi_url, params=params, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            lighthouse = data.get('lighthouseResult', {})
            audits = lighthouse.get('audits', {})
            categories = lighthouse.get('categories', {})

            performance_score = categories.get('performance', {}).get('score', 0)
            performance_score_100 = int(performance_score * 100) if performance_score else 0

            lcp = audits.get('largest-contentful-paint', {}).get('numericValue', 0) / 1000
            fid = audits.get('max-potential-fid', {}).get('numericValue', 0)
            cls_val = audits.get('cumulative-layout-shift', {}).get('numericValue', 0)
            speed_index = audits.get('speed-index', {}).get('numericValue', 0) / 1000
            fcp = audits.get('first-contentful-paint', {}).get('numericValue', 0) / 1000
            tbt = audits.get('total-blocking-time', {}).get('numericValue', 0)

            return {
                'score': performance_score_100,
                'lcp': round(lcp, 2),
                'fid': round(fid, 0),
                'cls': round(cls_val, 3),
                'speed_index': round(speed_index, 2),
                'fcp': round(fcp, 2),
                'tbt': round(tbt, 0),
            }
        else:
            logger.warning(f"PageSpeed API returned status {resp.status_code} for {strategy}: {resp.text[:200]}")
            return None
    except Exception as e:
        logger.warning(f"PageSpeed API error ({strategy}): {e}")
        return None


def _fetch_html_content(url, scrapingdog_api_key=None):
    """
    Fetch HTML via ScrapingDog with direct-request fallback.
    Returns (html_content, load_time) tuple. Raises on complete failure.
    """
    import requests as req
    import time

    start_time = time.time()
    html_content = None

    if scrapingdog_api_key:
        try:
            scrapingdog_url = "https://api.scrapingdog.com/scrape"
            params = {
                'api_key': scrapingdog_api_key,
                'url': url,
                'dynamic': 'false'
            }
            scrapingdog_response = req.get(scrapingdog_url, params=params, timeout=15)
            if scrapingdog_response.status_code == 200:
                html_content = scrapingdog_response.text
                logger.info(f"Successfully fetched {url} using ScrapingDog")
            else:
                logger.warning(f"ScrapingDog returned status {scrapingdog_response.status_code}. Falling back to direct request.")
        except Exception as sd_error:
            logger.warning(f"ScrapingDog error: {str(sd_error)}. Falling back to direct request.")

    if not html_content:
        response = req.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }, timeout=15)
        html_content = response.text
        logger.info(f"Successfully fetched {url} using direct request")

    load_time = time.time() - start_time
    return html_content, load_time


def _run_website_technical_checks(url, html_content, mobile_psi, desktop_psi):
    """
    Run all 11 Website Technical checks.
    Returns list of check dicts with category='website_technical'.
    Total max: 60 points.
    """
    import requests as req
    from urllib.parse import urljoin
    import re

    checks = []
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    # 1. Mobile Speed Index (5 pts)
    if mobile_psi:
        si = mobile_psi['speed_index']
        si_score = 5 if si < 3.4 else (3 if si < 5.8 else 0)
        si_status = 'pass' if si < 3.4 else ('warning' if si < 5.8 else 'fail')
        checks.append({
            'name': 'Mobile Speed Index',
            'category': 'website_technical',
            'status': si_status,
            'score': si_score,
            'max_score': 5,
            'message': f'Mobile Speed Index: {si}s' + (' (Good)' if si < 3.4 else ' (Needs Improvement)' if si < 5.8 else ' (Poor)'),
            'importance': 'high',
        })
    else:
        checks.append({
            'name': 'Mobile Speed Index',
            'category': 'website_technical',
            'status': 'warning',
            'score': 0,
            'max_score': 5,
            'message': 'Could not fetch PageSpeed data. Ensure GOOGLE_PAGESPEED_API_KEY is configured.',
            'importance': 'high',
        })

    # 2. Core Web Vital Assessment (Mobile) (8 pts)
    if mobile_psi:
        lcp_ok = mobile_psi['lcp'] <= 2.5
        fid_ok = mobile_psi['fid'] <= 100
        cls_ok = mobile_psi['cls'] <= 0.1
        cwv_passed = sum([lcp_ok, fid_ok, cls_ok])
        cwv_score = int(8 * (cwv_passed / 3))
        cwv_status = 'pass' if cwv_passed == 3 else ('warning' if cwv_passed >= 2 else 'fail')
        msg_parts = [
            f"LCP: {mobile_psi['lcp']}s ({'Good' if lcp_ok else 'Poor'})",
            f"FID: {int(mobile_psi['fid'])}ms ({'Good' if fid_ok else 'Poor'})",
            f"CLS: {mobile_psi['cls']} ({'Good' if cls_ok else 'Poor'})",
        ]
        checks.append({
            'name': 'Core Web Vital Assessment (Mobile)',
            'category': 'website_technical',
            'status': cwv_status,
            'score': cwv_score,
            'max_score': 8,
            'message': ' | '.join(msg_parts),
            'importance': 'high',
        })
    else:
        checks.append({
            'name': 'Core Web Vital Assessment (Mobile)',
            'category': 'website_technical',
            'status': 'warning',
            'score': 0,
            'max_score': 8,
            'message': 'Could not fetch PageSpeed data for mobile CWV assessment.',
            'importance': 'high',
        })

    # 3. Core Web Vital Assessment (Desktop) (7 pts)
    if desktop_psi:
        lcp_ok = desktop_psi['lcp'] <= 2.5
        fid_ok = desktop_psi['fid'] <= 100
        cls_ok = desktop_psi['cls'] <= 0.1
        cwv_passed = sum([lcp_ok, fid_ok, cls_ok])
        cwv_score = int(7 * (cwv_passed / 3))
        cwv_status = 'pass' if cwv_passed == 3 else ('warning' if cwv_passed >= 2 else 'fail')
        msg_parts = [
            f"LCP: {desktop_psi['lcp']}s ({'Good' if lcp_ok else 'Poor'})",
            f"FID: {int(desktop_psi['fid'])}ms ({'Good' if fid_ok else 'Poor'})",
            f"CLS: {desktop_psi['cls']} ({'Good' if cls_ok else 'Poor'})",
        ]
        checks.append({
            'name': 'Core Web Vital Assessment (Desktop)',
            'category': 'website_technical',
            'status': cwv_status,
            'score': cwv_score,
            'max_score': 7,
            'message': ' | '.join(msg_parts),
            'importance': 'high',
        })
    else:
        checks.append({
            'name': 'Core Web Vital Assessment (Desktop)',
            'category': 'website_technical',
            'status': 'warning',
            'score': 0,
            'max_score': 7,
            'message': 'Could not fetch PageSpeed data for desktop CWV assessment.',
            'importance': 'high',
        })

    # 4. Mobile Score (Out of 100) (5 pts)
    if mobile_psi:
        ms = mobile_psi['score']
        ms_score = 5 if ms >= 90 else (3 if ms >= 50 else 0)
        ms_status = 'pass' if ms >= 90 else ('warning' if ms >= 50 else 'fail')
        checks.append({
            'name': 'Mobile Score (Out of 100)',
            'category': 'website_technical',
            'status': ms_status,
            'score': ms_score,
            'max_score': 5,
            'message': f'Mobile Performance Score: {ms}/100',
            'importance': 'high',
        })
    else:
        checks.append({
            'name': 'Mobile Score (Out of 100)',
            'category': 'website_technical',
            'status': 'warning',
            'score': 0,
            'max_score': 5,
            'message': 'Could not fetch mobile performance score.',
            'importance': 'high',
        })

    # 5. Desktop Score (Out of 100) (5 pts)
    if desktop_psi:
        ds = desktop_psi['score']
        ds_score = 5 if ds >= 90 else (3 if ds >= 50 else 0)
        ds_status = 'pass' if ds >= 90 else ('warning' if ds >= 50 else 'fail')
        checks.append({
            'name': 'Desktop Score (Out of 100)',
            'category': 'website_technical',
            'status': ds_status,
            'score': ds_score,
            'max_score': 5,
            'message': f'Desktop Performance Score: {ds}/100',
            'importance': 'high',
        })
    else:
        checks.append({
            'name': 'Desktop Score (Out of 100)',
            'category': 'website_technical',
            'status': 'warning',
            'score': 0,
            'max_score': 5,
            'message': 'Could not fetch desktop performance score.',
            'importance': 'high',
        })

    # 6. Schema Tag (8 pts)
    schema_scripts = re.findall(r'<script\s+type=["\']application/ld\+json["\'][^>]*>.*?</script>', html_content, re.IGNORECASE | re.DOTALL)
    checks.append({
        'name': 'Schema Tag',
        'category': 'website_technical',
        'status': 'pass' if len(schema_scripts) > 0 else 'fail',
        'score': 8 if len(schema_scripts) > 0 else 0,
        'max_score': 8,
        'message': f'Found {len(schema_scripts)} structured data (Schema.org) blocks' if schema_scripts else 'No structured data (Schema.org) found',
        'importance': 'high',
    })

    # 7. Canonical Tags (5 pts)
    canonical_match = re.search(
        r'<link\s+[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',
        html_content, re.IGNORECASE
    )
    if not canonical_match:
        canonical_match = re.search(
            r'<link\s+[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']canonical["\']',
            html_content, re.IGNORECASE
        )
    canonical_url = canonical_match.group(1) if canonical_match else None
    checks.append({
        'name': 'Canonical Tags',
        'category': 'website_technical',
        'status': 'pass' if canonical_url else 'fail',
        'score': 5 if canonical_url else 0,
        'max_score': 5,
        'message': f'Canonical tag found: {canonical_url}' if canonical_url else 'No canonical tag found',
        'importance': 'medium',
    })

    # --- Checks 8-11: Fetch all URLs in parallel to avoid sequential delays ---
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _quick_get(path, timeout=3):
        """Quick HTTP GET helper, returns (path, response) or (path, None)."""
        try:
            resp = req.get(urljoin(url, path), timeout=timeout, allow_redirects=True,
                           headers={'User-Agent': USER_AGENT})
            return (path, resp)
        except Exception:
            return (path, None)

    # Fire all URL checks in parallel
    url_checks_to_make = [
        '/llms.txt', '/robots.txt',
        '/sitemap.xml', '/sitemap_index.xml', '/sitemap.xml.gz', '/sitemap.txt',
        '/sitemap', '/html-sitemap', '/sitemap.html', '/site-map',
    ]

    url_results = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_quick_get, p, 3): p for p in url_checks_to_make}
        for future in as_completed(futures):
            path, resp = future.result()
            url_results[path] = resp

    # 8. LLM Txt (3 pts)
    llms_resp = url_results.get('/llms.txt')
    llms_exists = llms_resp is not None and llms_resp.status_code == 200
    checks.append({
        'name': 'LLM Txt',
        'category': 'website_technical',
        'status': 'pass' if llms_exists else 'warning',
        'score': 3 if llms_exists else 0,
        'max_score': 3,
        'message': 'llms.txt found - provides AI crawler guidance' if llms_exists else 'llms.txt not found (recommended for AI optimization)',
        'importance': 'medium',
    })

    # 9. Robots.txt (4 pts)
    robots_resp = url_results.get('/robots.txt')
    robots_exists = robots_resp is not None and robots_resp.status_code == 200
    robots_text = robots_resp.text if robots_exists else ''
    checks.append({
        'name': 'Robots.txt',
        'category': 'website_technical',
        'status': 'pass' if robots_exists else 'warning',
        'score': 4 if robots_exists else 0,
        'max_score': 4,
        'message': 'robots.txt found' if robots_exists else 'robots.txt not found (optional but recommended)',
        'importance': 'medium',
    })

    # 10. XML Sitemap (5 pts) — check robots.txt directives first, then parallel results
    sitemap_found = False
    sitemap_location = None
    if robots_exists:
        for line in robots_text.split('\n'):
            line = line.strip()
            if line.lower().startswith('sitemap:'):
                sitemap_from_robots = line.split(':', 1)[1].strip()
                if sitemap_from_robots:
                    sitemap_found = True
                    sitemap_location = f"robots.txt ({sitemap_from_robots})"
                    break

    if not sitemap_found:
        for path in ['/sitemap.xml', '/sitemap_index.xml', '/sitemap.xml.gz', '/sitemap.txt']:
            resp = url_results.get(path)
            if resp is not None and resp.status_code == 200:
                content = resp.text[:500].lower()
                if '<?xml' in content or '<urlset' in content or '<sitemapindex' in content or 'http' in content:
                    sitemap_found = True
                    sitemap_location = path
                    break

    checks.append({
        'name': 'XML Sitemap',
        'category': 'website_technical',
        'status': 'pass' if sitemap_found else 'fail',
        'score': 5 if sitemap_found else 0,
        'max_score': 5,
        'message': f'Sitemap found at {sitemap_location}' if sitemap_found else 'No XML sitemap found',
        'importance': 'high',
    })

    # 11. HTML Sitemap (5 pts) — use parallel results
    html_sitemap_found = False
    html_sitemap_location = None
    for path in ['/sitemap', '/html-sitemap', '/sitemap.html', '/site-map']:
        resp = url_results.get(path)
        if resp is not None and resp.status_code == 200 and '<html' in resp.text[:1000].lower():
            if '<?xml' not in resp.text[:500].lower() and '<urlset' not in resp.text[:500].lower():
                html_sitemap_found = True
                html_sitemap_location = path
                break

    checks.append({
        'name': 'HTML Sitemap',
        'category': 'website_technical',
        'status': 'pass' if html_sitemap_found else 'warning',
        'score': 5 if html_sitemap_found else 0,
        'max_score': 5,
        'message': f'HTML sitemap found at {html_sitemap_location}' if html_sitemap_found else 'No HTML sitemap found (optional but recommended)',
        'importance': 'medium',
    })

    return checks


def _run_on_page_content_checks(url, html_content, scrapingdog_api_key=None):
    """
    Run all 6 On Page & Content checks.
    Returns list of check dicts with category='on_page_content'.
    Total max: 40 points.
    """
    import requests as req
    from urllib.parse import urljoin, urlparse
    import re

    from concurrent.futures import ThreadPoolExecutor, as_completed

    checks = []
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    def _quick_get(target_url, timeout=3):
        """Quick HTTP GET, returns response or None."""
        try:
            return req.get(target_url, timeout=timeout, allow_redirects=True,
                           headers={'User-Agent': USER_AGENT})
        except Exception:
            return None

    # --- Parallel Phase: Fire all HTTP checks at once ---
    blog_paths = ['/blog', '/blog/', '/news', '/news/', '/articles', '/articles/',
                  '/insights', '/insights/', '/resources', '/resources/']

    # Collect all URLs to check in parallel
    parallel_tasks = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        # Indexed pages via ScrapingDog
        if scrapingdog_api_key:
            parsed = urlparse(url)
            domain_name = parsed.netloc
            search_url = f"https://www.google.com/search?q=site:{domain_name}"
            parallel_tasks['indexed'] = pool.submit(
                lambda: req.get("https://api.scrapingdog.com/scrape",
                                params={'api_key': scrapingdog_api_key, 'url': search_url, 'dynamic': 'false'},
                                timeout=10)
            )

        # Blog path checks
        for path in blog_paths:
            parallel_tasks[f'blog:{path}'] = pool.submit(_quick_get, urljoin(url, path), 3)

        # Inner page links from HTML (for content check) — extract links first
        inner_links = re.findall(
            r'href=["\'](/(?:products?|category|categories|shop|services?|collections?)/[^"\'#?]+)["\']',
            html_content, re.IGNORECASE
        )
        sample_links = list(set(inner_links))[:3]
        for link in sample_links:
            parallel_tasks[f'inner:{link}'] = pool.submit(_quick_get, urljoin(url, link), 5)

        # Wait for all results
        results = {}
        for key, future in parallel_tasks.items():
            try:
                results[key] = future.result(timeout=15)
            except Exception:
                results[key] = None

    # 1. Total No. of Indexed Pages (5 pts)
    indexed_count = None
    indexed_resp = results.get('indexed')
    if indexed_resp is not None and indexed_resp.status_code == 200:
        result_match = re.search(r'About\s+([\d,]+)\s+results', indexed_resp.text)
        if not result_match:
            result_match = re.search(r'([\d,]+)\s+results', indexed_resp.text)
        if result_match:
            indexed_count = int(result_match.group(1).replace(',', ''))

    if indexed_count is not None:
        idx_score = 5 if indexed_count >= 50 else (3 if indexed_count >= 10 else 1)
        idx_status = 'pass' if indexed_count >= 50 else ('warning' if indexed_count >= 10 else 'fail')
        idx_msg = f'Approximately {indexed_count:,} pages indexed by Google'
    else:
        idx_score = 0
        idx_status = 'warning'
        idx_msg = 'Could not determine indexed page count. Check Google Search Console for accurate data.'

    checks.append({
        'name': 'Total No. of Indexed Pages',
        'category': 'on_page_content',
        'status': idx_status,
        'score': idx_score,
        'max_score': 5,
        'message': idx_msg,
        'importance': 'medium',
    })

    # 2. Blog Presence (7 pts) — use parallel results
    blog_found = False
    blog_path = None
    blog_resp_text = ''
    for path in blog_paths:
        resp = results.get(f'blog:{path}')
        if resp is not None and resp.status_code == 200 and len(resp.text) > 1000:
            blog_found = True
            blog_path = path
            blog_resp_text = resp.text
            break

    checks.append({
        'name': 'Blog Presence',
        'category': 'on_page_content',
        'status': 'pass' if blog_found else 'fail',
        'score': 7 if blog_found else 0,
        'max_score': 7,
        'message': f'Blog found at {blog_path}' if blog_found else 'No blog section found on the domain',
        'importance': 'high',
    })

    # 3. Frequency of Blog on Main Domain (7 pts) — reuse blog response from above
    blog_frequency_score = 0
    blog_freq_status = 'fail'
    blog_freq_msg = 'Could not determine blog posting frequency'
    if blog_found and blog_resp_text:
        date_patterns = re.findall(
            r'(\d{4}-\d{2}-\d{2})|(\w+\s+\d{1,2},?\s*\d{4})',
            blog_resp_text
        )
        if date_patterns:
            recent_count = len(date_patterns)
            if recent_count >= 8:
                blog_frequency_score = 7
                blog_freq_status = 'pass'
                blog_freq_msg = f'Active blog with ~{recent_count} recent posts detected'
            elif recent_count >= 3:
                blog_frequency_score = 4
                blog_freq_status = 'warning'
                blog_freq_msg = f'Blog moderately active with ~{recent_count} recent posts'
            else:
                blog_frequency_score = 2
                blog_freq_status = 'warning'
                blog_freq_msg = f'Blog appears infrequently updated ({recent_count} posts found)'
    elif not blog_found:
        blog_freq_msg = 'No blog found to check frequency'

    checks.append({
        'name': 'Frequency of Blog on Main Domain',
        'category': 'on_page_content',
        'status': blog_freq_status,
        'score': blog_frequency_score,
        'max_score': 7,
        'message': blog_freq_msg,
        'importance': 'medium',
    })

    # 4. Meta Tag Optimization (Title, Description, H1) (8 pts)
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
    title_text = title_match.group(1).strip() if title_match else None
    has_title = bool(title_text and len(title_text) > 0)

    meta_desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html_content, re.IGNORECASE)
    if not meta_desc_match:
        meta_desc_match = re.search(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']', html_content, re.IGNORECASE)
    meta_desc = meta_desc_match.group(1) if meta_desc_match else None
    has_desc = bool(meta_desc and len(meta_desc) > 0)

    h1_tags = re.findall(r'<h1[^>]*>(.*?)</h1>', html_content, re.IGNORECASE | re.DOTALL)
    has_h1 = len(h1_tags) >= 1

    # 3 pts title, 3 pts desc, 2 pts H1
    meta_score = (3 if has_title else 0) + (3 if has_desc else 0) + (2 if has_h1 else 0)
    meta_status = 'pass' if meta_score >= 7 else ('warning' if meta_score >= 4 else 'fail')
    msg_parts = []
    if has_title:
        msg_parts.append(f"Title: present ({len(title_text)} chars)")
    else:
        msg_parts.append("Title: MISSING")
    if has_desc:
        msg_parts.append(f"Description: present ({len(meta_desc)} chars)")
    else:
        msg_parts.append("Description: MISSING")
    msg_parts.append(f"H1 tags: {len(h1_tags)}" + (" (optimal)" if len(h1_tags) == 1 else ""))

    checks.append({
        'name': 'Meta Tag Optimization (Title, Description, H1)',
        'category': 'on_page_content',
        'status': meta_status,
        'score': meta_score,
        'max_score': 8,
        'message': ' | '.join(msg_parts),
        'importance': 'high',
    })

    # 5. Content on Category/Product Page (7 pts) — use parallel results
    content_score = 0
    content_status = 'warning'
    content_msg = 'No product/category pages detected in navigation'
    if sample_links:
        word_counts = []
        for link in sample_links:
            resp = results.get(f'inner:{link}')
            if resp is not None and resp.status_code == 200:
                text = re.sub(r'<[^>]+>', ' ', resp.text)
                text = re.sub(r'\s+', ' ', text).strip()
                word_counts.append(len(text.split()))
        if word_counts:
            avg_words = sum(word_counts) / len(word_counts)
            if avg_words >= 300:
                content_score = 7
                content_status = 'pass'
                content_msg = f'Good content depth on inner pages (avg ~{int(avg_words)} words across {len(word_counts)} sampled pages)'
            elif avg_words >= 100:
                content_score = 4
                content_status = 'warning'
                content_msg = f'Moderate content on inner pages (avg ~{int(avg_words)} words). Consider adding more descriptive content.'
            else:
                content_score = 1
                content_status = 'fail'
                content_msg = f'Thin content on inner pages (avg ~{int(avg_words)} words). Add more descriptive content.'

    checks.append({
        'name': 'Content on Category/Product Page',
        'category': 'on_page_content',
        'status': content_status,
        'score': content_score,
        'max_score': 7,
        'message': content_msg,
        'importance': 'medium',
    })

    # 6. FAQ on Category/Product Page (6 pts)
    faq_found = False
    faq_source = None

    # Check for FAQ schema in homepage
    faq_schema = re.search(r'"@type"\s*:\s*"FAQPage"', html_content, re.IGNORECASE)
    if faq_schema:
        faq_found = True
        faq_source = 'FAQPage schema detected on homepage'

    # Check for FAQ HTML sections
    if not faq_found:
        faq_section = re.search(
            r'(?:id|class)\s*=\s*["\'][^"\']*faq[^"\']*["\']',
            html_content, re.IGNORECASE
        )
        if faq_section:
            faq_found = True
            faq_source = 'FAQ section detected in HTML'

    # Check for accordion/FAQ patterns
    if not faq_found:
        faq_pattern = re.search(
            r'(?:id|class)\s*=\s*["\'][^"\']*(?:accordion|frequently-asked|questions)[^"\']*["\']',
            html_content, re.IGNORECASE
        )
        if faq_pattern:
            faq_found = True
            faq_source = 'FAQ/Accordion section detected in HTML'

    checks.append({
        'name': 'FAQ on Category/Product Page',
        'category': 'on_page_content',
        'status': 'pass' if faq_found else 'fail',
        'score': 6 if faq_found else 0,
        'max_score': 6,
        'message': faq_source if faq_found else 'No FAQ section or FAQPage schema found',
        'importance': 'medium',
    })

    return checks


def _fetch_moz_url_metrics(url):
    """
    Fetch URL metrics from Moz Free API (DA, PA, spam score, linking root domains, external links).
    Free tier: 2,500 rows/month, 1 request per 10 seconds.
    """
    import requests as req
    import base64

    access_id = getattr(settings, 'MOZ_ACCESS_ID', None)
    secret_key = getattr(settings, 'MOZ_SECRET_KEY', None)
    if not access_id or not secret_key:
        logger.warning("MOZ_ACCESS_ID or MOZ_SECRET_KEY not configured")
        return None

    try:
        auth_string = f"{access_id}:{secret_key}"
        auth_bytes = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

        response = req.post(
            'https://lsapi.seomoz.com/v2/url_metrics',
            headers={
                'Authorization': f'Basic {auth_bytes}',
                'Content-Type': 'application/json',
            },
            json={
                'targets': [url],
            },
            timeout=15,
        )
        if response.status_code == 200:
            data = response.json()
            if data and 'results' in data and len(data['results']) > 0:
                result = data['results'][0]
                return {
                    'domain_authority': result.get('domain_authority', 0),
                    'page_authority': result.get('page_authority', 0),
                    'spam_score': result.get('spam_score', 0),
                    'linking_root_domains': result.get('root_domains_to_root_domain', 0),
                    'external_links': result.get('external_pages_to_root_domain', 0),
                }
        else:
            logger.warning(f"Moz URL metrics API returned {response.status_code}: {response.text[:200]}")
            return None
    except Exception as e:
        logger.warning(f"Moz URL metrics API error: {e}")
        return None


def _fetch_moz_links(url, limit=50):
    """
    Fetch individual backlinks from Moz Free API.
    Returns list of links with source URL, source DA, anchor text.
    """
    import requests as req
    import base64
    from urllib.parse import urlparse

    access_id = getattr(settings, 'MOZ_ACCESS_ID', None)
    secret_key = getattr(settings, 'MOZ_SECRET_KEY', None)
    if not access_id or not secret_key:
        return None

    try:
        auth_string = f"{access_id}:{secret_key}"
        auth_bytes = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

        parsed = urlparse(url)
        target = parsed.netloc

        response = req.post(
            'https://lsapi.seomoz.com/v2/links',
            headers={
                'Authorization': f'Basic {auth_bytes}',
                'Content-Type': 'application/json',
            },
            json={
                'target': target,
                'target_type': 'root_domain',
                'limit': limit,
            },
            timeout=15,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])
        else:
            logger.warning(f"Moz Links API returned {response.status_code}: {response.text[:200]}")
            return None
    except Exception as e:
        logger.warning(f"Moz Links API error: {e}")
        return None


def _fetch_moz_anchor_text(url, limit=50):
    """
    Fetch anchor text data from Moz Free API.
    Returns list of anchor text entries.
    """
    import requests as req
    import base64
    from urllib.parse import urlparse

    access_id = getattr(settings, 'MOZ_ACCESS_ID', None)
    secret_key = getattr(settings, 'MOZ_SECRET_KEY', None)
    if not access_id or not secret_key:
        return None

    try:
        auth_string = f"{access_id}:{secret_key}"
        auth_bytes = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

        parsed = urlparse(url)
        target = parsed.netloc

        response = req.post(
            'https://lsapi.seomoz.com/v2/anchor_text',
            headers={
                'Authorization': f'Basic {auth_bytes}',
                'Content-Type': 'application/json',
            },
            json={
                'target': target,
                'target_type': 'root_domain',
                'limit': limit,
            },
            timeout=15,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])
        else:
            logger.warning(f"Moz Anchor Text API returned {response.status_code}: {response.text[:200]}")
            return None
    except Exception as e:
        logger.warning(f"Moz Anchor Text API error: {e}")
        return None


def _search_brand_mentions(brand_name, domain, scrapingdog_api_key=None):
    """
    Search Google for brand mentions using ScrapingDog.
    Returns (mentions_count, citations_count) tuple.
    """
    import requests as req
    import re
    from urllib.parse import urlparse

    mentions_count = 0
    citations_count = 0
    parsed = urlparse(domain)
    domain_name = parsed.netloc or domain

    if not scrapingdog_api_key:
        return mentions_count, citations_count

    try:
        # Brand mentions: search for brand name excluding own domain
        search_url = f'https://www.google.com/search?q="{brand_name}" -site:{domain_name}'
        params = {'api_key': scrapingdog_api_key, 'url': search_url, 'dynamic': 'false'}
        resp = req.get("https://api.scrapingdog.com/scrape", params=params, timeout=10)
        if resp.status_code == 200:
            result_match = re.search(r'About\s+([\d,]+)\s+results', resp.text)
            if not result_match:
                result_match = re.search(r'([\d,]+)\s+results', resp.text)
            if result_match:
                mentions_count = int(result_match.group(1).replace(',', ''))
    except Exception as e:
        logger.warning(f"Brand mentions search error: {e}")

    try:
        # Citations: search for domain mentions (NAP citations)
        search_url = f'https://www.google.com/search?q="{domain_name}" -site:{domain_name}'
        params = {'api_key': scrapingdog_api_key, 'url': search_url, 'dynamic': 'false'}
        resp = req.get("https://api.scrapingdog.com/scrape", params=params, timeout=10)
        if resp.status_code == 200:
            result_match = re.search(r'About\s+([\d,]+)\s+results', resp.text)
            if not result_match:
                result_match = re.search(r'([\d,]+)\s+results', resp.text)
            if result_match:
                citations_count = int(result_match.group(1).replace(',', ''))
    except Exception as e:
        logger.warning(f"Citations search error: {e}")

    return mentions_count, citations_count


def _run_website_authority_checks(url, brand_name, scrapingdog_api_key=None):
    """
    Run all 17 Website Authority checks using Moz Free API + Google search.
    Returns list of check dicts with category='website_authority'.

    Data sources:
    - Moz Free API: DA, PA, referring domains, backlinks, anchor text
    - Google Search via ScrapingDog: Brand mentions, citations
    - CAT A/B/C: Categorized by DA ranges (A: DA>=70, B: DA 40-69, C: DA<40)
    """
    from concurrent.futures import ThreadPoolExecutor

    checks = []

    # Fetch Moz data + brand mentions in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_metrics = executor.submit(_fetch_moz_url_metrics, url)
        future_links = executor.submit(_fetch_moz_links, url, 50)
        future_anchors = executor.submit(_fetch_moz_anchor_text, url, 50)
        future_brand = executor.submit(_search_brand_mentions, brand_name, url, scrapingdog_api_key)

        try:
            moz_metrics = future_metrics.result(timeout=20)
        except Exception:
            moz_metrics = None

        try:
            moz_links = future_links.result(timeout=20)
        except Exception:
            moz_links = None

        try:
            moz_anchors = future_anchors.result(timeout=20)
        except Exception:
            moz_anchors = None

        try:
            mentions_count, citations_count = future_brand.result(timeout=20)
        except Exception:
            mentions_count, citations_count = 0, 0

    moz_available = moz_metrics is not None

    # 1. Domain Rating (DA) — informational, no scoring
    da = moz_metrics.get('domain_authority', 0) if moz_available else 0
    checks.append({
        'name': 'Domain Rating',
        'category': 'website_authority',
        'status': 'pass' if da >= 30 else ('warning' if da >= 10 else 'fail') if moz_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'Domain Authority: {da}/100' if moz_available else 'Moz API not configured. Set MOZ_ACCESS_ID and MOZ_SECRET_KEY.',
        'importance': 'high',
    })

    # 2. URL Rating (PA) — informational
    pa = moz_metrics.get('page_authority', 0) if moz_available else 0
    checks.append({
        'name': 'URL Rating',
        'category': 'website_authority',
        'status': 'pass' if pa >= 30 else ('warning' if pa >= 10 else 'fail') if moz_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'Page Authority: {pa}/100' if moz_available else 'Moz API not configured.',
        'importance': 'high',
    })

    # 3. No. of Referring Domain — informational
    ref_domains = moz_metrics.get('linking_root_domains', 0) if moz_available else 0
    checks.append({
        'name': 'No. of Referring Domain',
        'category': 'website_authority',
        'status': 'pass' if ref_domains >= 50 else ('warning' if ref_domains >= 10 else 'fail') if moz_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'{ref_domains:,} referring domains' if moz_available else 'Moz API not configured.',
        'importance': 'high',
    })

    # Analyze links for CAT A/B/C and .gov/.edu breakdown
    cat_a_domains = set()
    cat_b_domains = set()
    cat_c_domains = set()
    cat_a_links = 0
    cat_b_links = 0
    cat_c_links = 0
    gov_links = 0
    edu_links = 0
    links_available = moz_links is not None and len(moz_links) > 0

    if links_available:
        for link in moz_links:
            source_da = link.get('source_domain_authority', 0) or 0
            source_url = link.get('source_page', '') or ''
            source_domain = link.get('source_root_domain', '') or ''

            # CAT classification by DA: A >= 70, B 40-69, C < 40
            if source_da >= 70:
                cat_a_domains.add(source_domain)
                cat_a_links += 1
            elif source_da >= 40:
                cat_b_domains.add(source_domain)
                cat_b_links += 1
            else:
                cat_c_domains.add(source_domain)
                cat_c_links += 1

            # .gov / .edu detection
            domain_lower = source_domain.lower()
            if domain_lower.endswith('.gov') or '.gov.' in domain_lower:
                gov_links += 1
            if domain_lower.endswith('.edu') or '.edu.' in domain_lower:
                edu_links += 1

    # 4. CAT A Referring Domain (DA >= 70) — informational
    checks.append({
        'name': 'CAT A Referring Domain',
        'category': 'website_authority',
        'status': 'pass' if len(cat_a_domains) > 0 else 'warning' if links_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'{len(cat_a_domains)} high-authority referring domains (DA >= 70)' if links_available else 'No link data available.',
        'importance': 'medium',
    })

    # 5. CAT B Referring Domain (DA 40-69) — informational
    checks.append({
        'name': 'CAT B Referring Domain',
        'category': 'website_authority',
        'status': 'pass' if len(cat_b_domains) > 0 else 'warning' if links_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'{len(cat_b_domains)} medium-authority referring domains (DA 40-69)' if links_available else 'No link data available.',
        'importance': 'medium',
    })

    # 6. CAT C Referring Domain (DA < 40) — informational
    checks.append({
        'name': 'CAT C Referring Domain',
        'category': 'website_authority',
        'status': 'pass' if len(cat_c_domains) > 0 else 'warning' if links_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'{len(cat_c_domains)} low-authority referring domains (DA < 40)' if links_available else 'No link data available.',
        'importance': 'medium',
    })

    # 7. Total Backlinks — informational
    total_backlinks = moz_metrics.get('external_links', 0) if moz_available else 0
    checks.append({
        'name': 'Total Backlinks',
        'category': 'website_authority',
        'status': 'pass' if total_backlinks >= 100 else ('warning' if total_backlinks >= 10 else 'fail') if moz_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'{total_backlinks:,} total backlinks' if moz_available else 'Moz API not configured.',
        'importance': 'high',
    })

    # 8. CAT A Backlinks (from DA >= 70 sources) — informational
    checks.append({
        'name': 'CAT A Backlinks',
        'category': 'website_authority',
        'status': 'pass' if cat_a_links > 0 else 'warning' if links_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'{cat_a_links} backlinks from high-authority sources (DA >= 70)' if links_available else 'No link data available.',
        'importance': 'medium',
    })

    # 9. CAT B Backlinks (from DA 40-69 sources) — informational
    checks.append({
        'name': 'CAT B Backlinks',
        'category': 'website_authority',
        'status': 'pass' if cat_b_links > 0 else 'warning' if links_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'{cat_b_links} backlinks from medium-authority sources (DA 40-69)' if links_available else 'No link data available.',
        'importance': 'medium',
    })

    # 10. CAT C Backlinks (from DA < 40 sources) — informational
    checks.append({
        'name': 'CAT C Backlinks',
        'category': 'website_authority',
        'status': 'pass' if cat_c_links > 0 else 'warning' if links_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'{cat_c_links} backlinks from low-authority sources (DA < 40)' if links_available else 'No link data available.',
        'importance': 'medium',
    })

    # 11. Total .gov Backlinks — informational
    checks.append({
        'name': 'Total .gov Backlinks',
        'category': 'website_authority',
        'status': 'pass' if gov_links > 0 else 'warning' if links_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'{gov_links} backlinks from .gov domains' if links_available else 'No link data available.',
        'importance': 'medium',
    })

    # 12. Total .edu Backlinks — informational
    checks.append({
        'name': 'Total .edu Backlinks',
        'category': 'website_authority',
        'status': 'pass' if edu_links > 0 else 'warning' if links_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'{edu_links} backlinks from .edu domains' if links_available else 'No link data available.',
        'importance': 'medium',
    })

    # 13. Brand Mentions — informational
    checks.append({
        'name': 'Brand Mentions',
        'category': 'website_authority',
        'status': 'pass' if mentions_count >= 100 else ('warning' if mentions_count > 0 else 'fail'),
        'score': 0,
        'max_score': 0,
        'message': f'~{mentions_count:,} brand mentions found on the web' if mentions_count > 0 else 'No brand mentions detected or unable to search.',
        'importance': 'medium',
    })

    # 14. Citations — informational
    checks.append({
        'name': 'Citations',
        'category': 'website_authority',
        'status': 'pass' if citations_count >= 100 else ('warning' if citations_count > 0 else 'fail'),
        'score': 0,
        'max_score': 0,
        'message': f'~{citations_count:,} domain citations found on the web' if citations_count > 0 else 'No citations detected or unable to search.',
        'importance': 'medium',
    })

    # Analyze anchor text
    anchors_available = moz_anchors is not None and len(moz_anchors) > 0
    total_anchors = 0
    branded_anchors = 0
    non_branded_anchors = 0

    if anchors_available:
        brand_lower = brand_name.lower() if brand_name else ''
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain_parts = parsed.netloc.lower().replace('www.', '').split('.')
        domain_keyword = domain_parts[0] if domain_parts else ''

        for anchor in moz_anchors:
            anchor_text = (anchor.get('anchor_text', '') or '').strip().lower()
            if not anchor_text:
                continue
            total_anchors += 1
            # Check if anchor text contains brand name or domain name
            if (brand_lower and brand_lower in anchor_text) or (domain_keyword and domain_keyword in anchor_text):
                branded_anchors += 1
            else:
                non_branded_anchors += 1

    # 15. Total Anchor Text — informational
    checks.append({
        'name': 'Total Anchor Text',
        'category': 'website_authority',
        'status': 'pass' if total_anchors >= 10 else ('warning' if total_anchors > 0 else 'fail') if anchors_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'{total_anchors} unique anchor texts found' if anchors_available else 'Anchor text data not available. Configure Moz API.',
        'importance': 'medium',
    })

    # 16. Branded Anchor Text — informational
    checks.append({
        'name': 'Branded Anchor Text',
        'category': 'website_authority',
        'status': 'pass' if branded_anchors > 0 else 'warning' if anchors_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'{branded_anchors} branded anchor texts (containing "{brand_name}")' if anchors_available else 'Anchor text data not available.',
        'importance': 'medium',
    })

    # 17. Non Branded Anchor Text — informational
    checks.append({
        'name': 'Non Branded Anchor Text',
        'category': 'website_authority',
        'status': 'pass' if non_branded_anchors > 0 else 'warning' if anchors_available else 'warning',
        'score': 0,
        'max_score': 0,
        'message': f'{non_branded_anchors} non-branded anchor texts' if anchors_available else 'Anchor text data not available.',
        'importance': 'medium',
    })

    return checks


def _reconstruct_categories_from_checks(checks_list):
    """Rebuild categories from flat check list using the 'category' field."""
    category_names = {
        'website_technical': 'Website Technical',
        'on_page_content': 'On Page & Content',
        'website_authority': 'Website Authority',
    }
    category_order = ['website_technical', 'on_page_content', 'website_authority']

    cat_map = {}
    for c in checks_list:
        cat_key = c.get('category', 'website_technical')
        if cat_key not in cat_map:
            cat_map[cat_key] = []
        cat_map[cat_key].append(c)

    categories = []
    for key in category_order:
        if key in cat_map:
            cat_checks = cat_map[key]
            categories.append({
                'name': category_names.get(key, key),
                'key': key,
                'checks': cat_checks,
                'summary': {
                    'total': len(cat_checks),
                    'passed': len([c for c in cat_checks if c['status'] == 'pass']),
                    'warnings': len([c for c in cat_checks if c['status'] == 'warning']),
                    'failed': len([c for c in cat_checks if c['status'] == 'fail']),
                },
                'score': sum(c['score'] for c in cat_checks),
                'max_score': sum(c['max_score'] for c in cat_checks),
            })

    # Handle any uncategorized checks (from old records without category field)
    uncategorized = [c for c in checks_list if c.get('category') not in category_order and 'category' not in c]
    if uncategorized:
        categories.insert(0, {
            'name': 'Website Technical',
            'key': 'website_technical',
            'checks': uncategorized,
            'summary': {
                'total': len(uncategorized),
                'passed': len([c for c in uncategorized if c['status'] == 'pass']),
                'warnings': len([c for c in uncategorized if c['status'] == 'warning']),
                'failed': len([c for c in uncategorized if c['status'] == 'fail']),
            },
            'score': sum(c['score'] for c in uncategorized),
            'max_score': sum(c['max_score'] for c in uncategorized),
        })

    return categories


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def domain_health_check(request, domain_id):
    """
    Perform comprehensive health checks on a domain.
    Checks are organized into categories: Website Technical, On Page & Content, Website Authority.
    Uses Google PageSpeed Insights API for performance metrics and ScrapingDog for web scraping.
    """
    import requests as req
    from concurrent.futures import ThreadPoolExecutor

    try:
        domain = get_object_or_404(Domain, id=domain_id)
        url = domain.url

        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        scrapingdog_api_key = getattr(settings, "SCRAPINGDOG_API_KEY", None)

        # Run data fetching + checks in parallel
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=5) as executor:
            # Independent data fetches
            future_html = executor.submit(_fetch_html_content, url, scrapingdog_api_key)
            future_mobile = executor.submit(_fetch_pagespeed_data, url, 'mobile')
            future_desktop = executor.submit(_fetch_pagespeed_data, url, 'desktop')

            # Wait for HTML first (needed by technical + content checks)
            html_content = ''
            load_time = 0
            try:
                html_content, load_time = future_html.result(timeout=30)
            except Exception as e:
                logger.error(f"Error fetching domain {url}: {str(e)}")
                future_mobile.cancel()
                future_desktop.cancel()
                return Response({
                    'success': False,
                    'error': f'Unable to access website: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Wait for PageSpeed (with short timeout since they started in parallel with HTML)
            mobile_psi = None
            desktop_psi = None
            try:
                mobile_psi = future_mobile.result(timeout=30)
            except Exception:
                logger.warning(f"PageSpeed mobile timed out for {url}")
            try:
                desktop_psi = future_desktop.result(timeout=30)
            except Exception:
                logger.warning(f"PageSpeed desktop timed out for {url}")

            # Run technical + content checks in parallel
            future_technical = executor.submit(
                _run_website_technical_checks, url, html_content, mobile_psi, desktop_psi
            )
            future_content = executor.submit(
                _run_on_page_content_checks, url, html_content, scrapingdog_api_key
            )

            technical_checks = future_technical.result(timeout=60)
            content_checks = future_content.result(timeout=60)

        # Website Authority — disabled until Moz API is purchased
        # To enable: uncomment the line below and remove the placeholder
        # authority_checks = _run_website_authority_checks(url, domain.name, scrapingdog_api_key)
        authority_checks = []

        # Step 4: Build categories with summaries
        def _build_category(name, key, checks_list):
            return {
                'name': name,
                'key': key,
                'checks': checks_list,
                'summary': {
                    'total': len(checks_list),
                    'passed': len([c for c in checks_list if c['status'] == 'pass']),
                    'warnings': len([c for c in checks_list if c['status'] == 'warning']),
                    'failed': len([c for c in checks_list if c['status'] == 'fail']),
                },
                'score': sum(c['score'] for c in checks_list),
                'max_score': sum(c['max_score'] for c in checks_list),
            }

        categories = [
            _build_category('Website Technical', 'website_technical', technical_checks),
            _build_category('On Page & Content', 'on_page_content', content_checks),
            {
                'name': 'Website Authority',
                'key': 'website_authority',
                'status': 'coming_soon',
                'checks': [
                    {'name': n, 'status': 'coming_soon', 'score': 0, 'max_score': 0}
                    for n in [
                        'Domain Rating', 'URL Rating', 'No. of Referring Domain',
                        'CAT A Referring Domain', 'CAT B Referring Domain', 'CAT C Referring Domain',
                        'Total Backlinks', 'CAT A Backlinks', 'CAT B Backlinks', 'CAT C Backlinks',
                        'Total .gov Backlinks', 'Total .edu Backlinks',
                        'Brand Mentions', 'Citations',
                        'Total Anchor Text', 'Branded Anchor Text', 'Non Branded Anchor Text',
                    ]
                ],
                'summary': {'total': 17, 'passed': 0, 'warnings': 0, 'failed': 0},
                'score': 0,
                'max_score': 0,
                'placeholder_message': 'Website Authority checks require Moz API. These checks will be enabled once configured.',
            },
        ]

        # Step 5: Calculate totals (only technical + content contribute to score)
        all_checks = technical_checks + content_checks
        health_score = sum(c['score'] for c in all_checks)
        max_score = sum(c['max_score'] for c in all_checks)
        health_percentage = int((health_score / max_score) * 100) if max_score > 0 else 0

        # Grade thresholds
        if health_percentage >= 80:
            grade, grade_color = 'Excellent', 'green'
        elif health_percentage >= 60:
            grade, grade_color = 'Good', 'blue'
        elif health_percentage >= 40:
            grade, grade_color = 'Fair', 'yellow'
        else:
            grade, grade_color = 'Poor', 'red'

        summary = {
            'total_checks': len(all_checks),
            'passed': len([c for c in all_checks if c['status'] == 'pass']),
            'warnings': len([c for c in all_checks if c['status'] == 'warning']),
            'failed': len([c for c in all_checks if c['status'] == 'fail']),
        }

        # Step 6: Save to DB
        from .models import DomainHealthCheck
        health_check = DomainHealthCheck.objects.create(
            domain=domain,
            health_score=health_score,
            max_score=max_score,
            percentage=health_percentage,
            grade=grade,
            grade_color=grade_color,
            checks=all_checks,
            total_checks=summary['total_checks'],
            passed_checks=summary['passed'],
            warning_checks=summary['warnings'],
            failed_checks=summary['failed'],
            checked_by=request.user
        )

        # Step 7: Return response with both flat and categorized data
        return Response({
            'success': True,
            'id': health_check.id,
            'domain': {
                'id': domain.id,
                'name': domain.name,
                'url': domain.url
            },
            'health_score': health_score,
            'max_score': max_score,
            'percentage': health_percentage,
            'grade': grade,
            'grade_color': grade_color,
            'checks': all_checks,
            'categories': categories,
            'summary': summary,
            'created_at': health_check.created_at.isoformat()
        })

    except Exception as e:
        logger.error(f"Error in domain health check: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def domain_health_check_history(request, domain_id):
    """
    Get health check history for a domain
    Returns list of past health checks with optional limit
    """
    from .models import DomainHealthCheck

    try:
        domain = get_object_or_404(Domain, id=domain_id)

        # Get limit from query params (default 10, max 100)
        limit = request.GET.get('limit', '10')
        try:
            limit = int(limit)
            if limit > 100:
                limit = 100
        except ValueError:
            limit = 10

        # Get health check history
        health_checks = DomainHealthCheck.objects.filter(
            domain=domain
        ).order_by('-created_at')[:limit]

        # Serialize the data
        history = []
        for check in health_checks:
            history.append({
                'id': check.id,
                'health_score': check.health_score,
                'max_score': check.max_score,
                'percentage': check.percentage,
                'grade': check.grade,
                'grade_color': check.grade_color,
                'checks': check.checks,
                'categories': _reconstruct_categories_from_checks(check.checks),
                'summary': {
                    'total_checks': check.total_checks,
                    'passed': check.passed_checks,
                    'warnings': check.warning_checks,
                    'failed': check.failed_checks
                },
                'checked_by': {
                    'id': check.checked_by.id if check.checked_by else None,
                    'email': check.checked_by.email if check.checked_by else None,
                    'first_name': check.checked_by.first_name if check.checked_by else None,
                    'last_name': check.checked_by.last_name if check.checked_by else None,
                } if check.checked_by else None,
                'created_at': check.created_at.isoformat()
            })

        # Get latest check for comparison
        latest_check = health_checks.first() if health_checks.exists() else None

        # Calculate trend if we have at least 2 checks
        trend = None
        if len(history) >= 2:
            current_score = history[0]['percentage']
            previous_score = history[1]['percentage']
            trend = {
                'direction': 'up' if current_score > previous_score else 'down' if current_score < previous_score else 'stable',
                'change': current_score - previous_score
            }

        return Response({
            'success': True,
            'domain': {
                'id': domain.id,
                'name': domain.name,
                'url': domain.url
            },
            'history': history,
            'trend': trend,
            'total_checks': DomainHealthCheck.objects.filter(domain=domain).count()
        })

    except Exception as e:
        logger.error(f"Error fetching health check history: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def automated_domain_onboard(request):
    """
    Automated domain onboarding - triggers full processing pipeline.
    This endpoint:
    1. Fetches brand niches (if not provided)
    2. Generates semantic keywords
    3. Creates the domain with processing status
    4. Returns domain ID for frontend to poll status

    Frontend will show loading modal with progress messages while this processes.
    """
    # Only admins can create domains
    if request.user.role not in ['admin', 'super_admin']:
        return Response(
            {'error': 'Only organization administrators can add domains'},
            status=status.HTTP_403_FORBIDDEN
        )

    domain_name = request.data.get('domain_name', '').strip()
    brand_name = request.data.get('brand_name', '').strip()
    country_code = request.data.get('country', 'us')
    niches = request.data.get('niches', [])

    if not domain_name:
        return Response(
            {'error': 'domain_name is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not brand_name:
        return Response(
            {'error': 'brand_name is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Convert country code to country name
        country_map = {
            'us': 'United States', 'gb': 'United Kingdom', 'ca': 'Canada',
            'au': 'Australia', 'de': 'Germany', 'fr': 'France', 'es': 'Spain',
            'it': 'Italy', 'jp': 'Japan', 'in': 'India', 'br': 'Brazil',
            'mx': 'Mexico', 'nl': 'Netherlands', 'se': 'Sweden', 'no': 'Norway',
            'dk': 'Denmark', 'fi': 'Finland', 'pl': 'Poland', 'be': 'Belgium',
            'at': 'Austria', 'ch': 'Switzerland', 'ie': 'Ireland',
            'nz': 'New Zealand', 'sg': 'Singapore'
        }
        country_name = country_map.get(country_code.lower(), 'United States')

        # Normalize domain
        normalized_domain = domain_name.lower()
        if normalized_domain.startswith('http://'):
            normalized_domain = normalized_domain[len('http://'):]
        elif normalized_domain.startswith('https://'):
            normalized_domain = normalized_domain[len('https://'):]
        if normalized_domain.startswith('www.'):
            normalized_domain = normalized_domain[4:]
        for sep in ['/', '?', '#']:
            if sep in normalized_domain:
                normalized_domain = normalized_domain.split(sep, 1)[0]
        if ':' in normalized_domain:
            normalized_domain = normalized_domain.split(':', 1)[0]

        domain_url = f"https://{normalized_domain}"

        # Step 1: Fetch niches if not provided (Progress: Analyzing your top niches)
        if not niches or len(niches) == 0:
            try:
                genai = get_google_genai_client()
                model = genai.GenerativeModel('gemini-2.0-flash')

                prompt = f"""Analyze the brand "{brand_name}" (website: {domain_name}) and suggest relevant industry niches or categories.

Return ONLY a JSON array of 5-8 specific industry niches/categories that best describe this brand's market positioning.
Example format: ["Enterprise SaaS", "Cloud Infrastructure", "DevOps Tools"]

Provide the response as a valid JSON array only, no additional text."""

                response = model.generate_content(prompt)
                result_text = response.text.strip()

                # Parse niches
                if result_text.startswith('```'):
                    result_text = result_text.split('```')[1]
                    if result_text.startswith('json'):
                        result_text = result_text[4:]
                    result_text = result_text.strip()

                niches = json.loads(result_text)
                if not isinstance(niches, list):
                    niches = []
                niches = [str(n).strip() for n in niches if n][:10]

            except Exception as e:
                logger.error(f"Error fetching niches: {str(e)}")
                niches = []  # Continue with empty niches

        # Step 2: Generate semantic keywords (Progress: Finding the best topics)
        generated_keywords = []
        try:
            genai = get_google_genai_client()
            model = genai.GenerativeModel('gemini-2.0-flash')

            niche_text = ", ".join(niches) if niches else "general business"
            max_keywords = 50

            prompt = f"""You are an expert SEO keyword researcher. Generate a comprehensive keyword universe for:

**Website:** {domain_name}
**Brand Name:** {brand_name}
**Country:** {country_name}
**Industry Niches:** {niche_text}
**Number of Keywords:** EXACTLY {max_keywords} unique, relevant keywords

Generate keywords that cover:
- Brand-related queries
- Product/service queries
- Informational queries
- Commercial/transactional queries

For each keyword, provide:
1. **keyword**: The actual keyword phrase
2. **volume_level**: Estimated search volume (very-low, low, medium, high, very-high)
3. **intent**: Search intent type (informational, navigational, transactional, commercial)
4. **entity**: Main subject/noun of the keyword
5. **attribute**: Characteristic being queried (if applicable)
6. **variable**: Modifier/qualifier (if applicable)
7. **source**: Always set to "ai-generated"
8. **topic**: Main topic/category
9. **cluster_id**: Group identifier for related keywords

Return ONLY a valid JSON object with this structure:
{{
  "project": {{
    "country": "{country_name}",
    "language": "en",
    "website": "{domain_name}",
    "niche": "{niche_text}",
    "approx_keywords_requested": {max_keywords}
  }},
  "keywords": [
    {{
      "keyword": "example keyword",
      "volume_level": "medium",
      "intent": "informational",
      "entity": "product",
      "attribute": "price",
      "variable": "cheap",
      "source": "ai-generated",
      "topic": "pricing",
      "cluster_id": "cluster_1"
    }}
  ]
}}"""

            response = model.generate_content(prompt)
            result_text = response.text.strip()

            # Parse keywords
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            if not result_text.startswith('{'):
                start = result_text.find('{')
                if start != -1:
                    result_text = result_text[start:]

            data = json.loads(result_text)
            if 'keywords' in data and isinstance(data['keywords'], list):
                generated_keywords = data['keywords']

        except Exception as e:
            logger.error(f"Error generating keywords: {str(e)}")
            # Continue with empty keywords - domain will still be created

        # Step 3: Fetch brand info from ChatGPT
        brand_info = {}
        try:
            client = get_openai_client()

            prompt = f"""Analyze the brand/website "{brand_name}" ({domain_url}) and provide the following information in JSON format.

Return ONLY a valid JSON object with these fields:
{{
    "short_description": "A brief 1-2 sentence description of what this brand/company does",
    "target_audience": "Description of the primary target audience demographics, interests, and needs",
    "brand_values": "Core values and principles the brand likely stands for (as a comma-separated list)",
    "key_competitors": "List of 3-5 likely competitors in the same space (as a comma-separated list)",
    "tone_of_voice": "Recommended tone of voice for content (e.g., professional, friendly, authoritative)",
    "content_style": "Recommended content style guidelines (e.g., concise, detailed, technical)",
    "key_messages": "Key messages or themes the brand should emphasize",
    "topics_to_avoid": "Topics or themes the brand should avoid in content"
}}"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a brand analyst expert. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            result_text = response.choices[0].message.content.strip()

            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            brand_info = json.loads(result_text)

        except Exception as e:
            logger.error(f"Error fetching brand info: {str(e)}")
            # Continue without brand info

        # Step 4: Create domain with all collected data
        with transaction.atomic():
            # Prepare keywords string (all generated keywords)
            keywords_str = ','.join([kw.get('keyword', '') for kw in generated_keywords if kw.get('keyword')])

            # Create domain
            domain = Domain.objects.create(
                name=brand_name,
                url=domain_url,
                organisation=request.user.organisation,
                country=country_name,
                niches=niches if niches else [],
                processing_status='COMP',  # Set to COMP immediately as we've done all processing
                short_description=brand_info.get('short_description', ''),
                target_audience=brand_info.get('target_audience', ''),
                brand_values=brand_info.get('brand_values', ''),
                key_competitors=brand_info.get('key_competitors', ''),
                tone_of_voice=brand_info.get('tone_of_voice', ''),
                content_style=brand_info.get('content_style', ''),
                key_messages=brand_info.get('key_messages', ''),
                topics_to_avoid=brand_info.get('topics_to_avoid', ''),
            )

            # Save all generated keywords to secondary_keywords table
            if generated_keywords:
                try:
                    from keywords.models import SecondaryKeyword
                    for kw_data in generated_keywords:
                        SecondaryKeyword.objects.create(
                            domain=domain,
                            keyword=kw_data.get('keyword', ''),
                            volume_level=kw_data.get('volume_level', 'medium'),
                            intent=kw_data.get('intent', 'informational'),
                            entity=kw_data.get('entity', ''),
                            attribute=kw_data.get('attribute', ''),
                            variable=kw_data.get('variable', ''),
                            source='ai-generated',
                            topic=kw_data.get('topic', ''),
                            cluster_id=kw_data.get('cluster_id', ''),
                        )
                except Exception as e:
                    logger.error(f"Error creating secondary keywords: {str(e)}")

            # Grant access to the creating admin
            try:
                DomainAccess.objects.create(
                    domain=domain,
                    user=request.user,
                    granted_by=request.user
                )
            except Exception as e:
                logger.error(f"Error creating domain access: {str(e)}")

        return Response({
            'success': True,
            'message': 'Domain created successfully',
            'domain': {
                'id': domain.id,
                'name': domain.name,
                'url': domain.url,
                'country': domain.country,
                'niches': domain.niches,
                'processing_status': domain.processing_status,
                'short_description': domain.short_description,
                'target_audience': domain.target_audience,
                'brand_values': domain.brand_values,
                'key_competitors': domain.key_competitors,
                'tone_of_voice': domain.tone_of_voice,
                'content_style': domain.content_style,
                'key_messages': domain.key_messages,
                'topics_to_avoid': domain.topics_to_avoid,
            },
            'keywords_generated': len(generated_keywords),
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error in automated domain onboarding: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Internal Link Map Management
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def internal_link_map_list(request, domain_id):
    """
    List all internal link mappings for a domain or create a new one
    """
    # Verify domain access
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
            {'error': 'Domain not found or you do not have access to this domain'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        links = InternalLinkMap.objects.filter(domain=domain)
        serializer = InternalLinkMapSerializer(links, many=True)
        return Response({
            'internal_links': serializer.data,
            'total': links.count()
        })

    elif request.method == 'POST':
        # Only admins can create internal links
        if request.user.role not in ['admin', 'super_admin']:
            return Response(
                {'error': 'Only organization administrators can manage internal links'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = InternalLinkMapCreateSerializer(data=request.data)
        if serializer.is_valid():
            link = serializer.save(domain=domain)
            return Response({
                'message': 'Internal link created successfully',
                'link': InternalLinkMapSerializer(link).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def internal_link_map_detail(request, domain_id, link_id):
    """
    Retrieve, update or delete an internal link mapping
    """
    # Verify domain access
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
            {'error': 'Domain not found or you do not have access to this domain'},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        link = InternalLinkMap.objects.get(pk=link_id, domain=domain)
    except InternalLinkMap.DoesNotExist:
        return Response(
            {'error': 'Internal link not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        serializer = InternalLinkMapSerializer(link)
        return Response(serializer.data)

    elif request.method == 'PUT':
        if request.user.role not in ['admin', 'super_admin']:
            return Response(
                {'error': 'Only organization administrators can update internal links'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = InternalLinkMapCreateSerializer(link, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Internal link updated successfully',
                'link': InternalLinkMapSerializer(link).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        if request.user.role not in ['admin', 'super_admin']:
            return Response(
                {'error': 'Only organization administrators can delete internal links'},
                status=status.HTTP_403_FORBIDDEN
            )

        link.delete()
        return Response({
            'message': 'Internal link deleted successfully'
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def internal_link_map_import_csv(request, domain_id):
    """
    Import internal link mappings from CSV data
    Expected CSV format: topic,keywords,url (with header row)
    """
    # Verify domain access and admin permission
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
            {'error': 'Domain not found or you do not have access to this domain'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.user.role not in ['admin', 'super_admin']:
        return Response(
            {'error': 'Only organization administrators can import internal links'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Get CSV data from request
    csv_data = request.data.get('csv_data', [])
    if not csv_data or not isinstance(csv_data, list):
        return Response(
            {'error': 'csv_data must be a non-empty array of objects with topic, keywords, and url fields'},
            status=status.HTTP_400_BAD_REQUEST
        )

    created_count = 0
    errors = []

    with transaction.atomic():
        for index, row in enumerate(csv_data):
            topic = row.get('topic', '').strip()
            keywords = row.get('keywords', '').strip()
            url = row.get('url', '').strip()

            if not topic or not keywords or not url:
                errors.append(f"Row {index + 1}: Missing required fields (topic, keywords, or url)")
                continue

            if not url.startswith(('http://', 'https://')):
                errors.append(f"Row {index + 1}: URL must start with http:// or https://")
                continue

            try:
                InternalLinkMap.objects.create(
                    domain=domain,
                    topic=topic,
                    keywords=keywords,
                    url=url
                )
                created_count += 1
            except Exception as e:
                errors.append(f"Row {index + 1}: {str(e)}")

    return Response({
        'message': f'Successfully imported {created_count} internal link(s)',
        'created_count': created_count,
        'errors': errors if errors else None
    }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)


# ===== Reference Repository =====

def _extract_text_from_file(file_obj, file_type):
    """
    Extract plain text from uploaded file.
    Returns extracted text string.
    Handles large files (up to 25MB) with batched processing to avoid
    memory issues.
    """
    import io

    MAX_PDF_PAGES = 300  # Safety limit for very large PDFs
    PDF_BATCH_SIZE = 50  # Process pages in batches to manage memory
    OCR_BATCH_SIZE = 20  # Smaller batches for memory-heavy OCR
    OCR_MAX_PAGES = 100  # OCR is expensive — limit pages for scanned PDFs

    file_obj.seek(0)
    file_bytes = file_obj.read()
    file_obj.seek(0)

    if file_type == 'pdf':
        # Step 1: Try pdfplumber (fast, works for text-based PDFs)
        # Process in batches to manage memory for large documents
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                total_pages = len(pdf.pages)
                pages_to_process = min(total_pages, MAX_PDF_PAGES)
                if total_pages > MAX_PDF_PAGES:
                    logger.warning(
                        f"PDF has {total_pages} pages, processing only "
                        f"first {MAX_PDF_PAGES} to avoid excessive memory usage"
                    )

                pages_text = []
                # Process in batches to avoid holding all page objects in memory
                for batch_start in range(0, pages_to_process, PDF_BATCH_SIZE):
                    batch_end = min(batch_start + PDF_BATCH_SIZE, pages_to_process)
                    for i in range(batch_start, batch_end):
                        try:
                            text = pdf.pages[i].extract_text()
                            if text:
                                pages_text.append(text)
                        except Exception as page_err:
                            logger.warning(f"Failed to extract page {i+1}: {page_err}")
                            continue

                if pages_text:
                    logger.info(
                        f"PDF text extraction: {len(pages_text)}/{pages_to_process} "
                        f"pages extracted successfully"
                    )
                    return '\n\n'.join(pages_text)
        except Exception as e:
            logger.warning(f"PDF pdfplumber extraction failed: {e}")

        # Step 2: Fallback to OCR for scanned/image PDFs
        # Process in small batches to avoid loading all images into memory at once
        try:
            from pdf2image import convert_from_bytes
            import pytesseract

            logger.info("PDF text extraction empty, attempting OCR fallback")

            # Get total page count first without converting
            try:
                from pdf2image import pdfinfo_from_bytes
                info = pdfinfo_from_bytes(file_bytes)
                total_pages = info.get('Pages', 0)
            except Exception:
                total_pages = OCR_MAX_PAGES  # Assume max if we can't determine

            pages_to_ocr = min(total_pages, OCR_MAX_PAGES)
            if total_pages > OCR_MAX_PAGES:
                logger.warning(
                    f"Scanned PDF has {total_pages} pages, OCR limited to "
                    f"first {OCR_MAX_PAGES} pages"
                )

            ocr_pages = []
            # Process OCR in small batches to limit memory usage
            for batch_start in range(0, pages_to_ocr, OCR_BATCH_SIZE):
                batch_end = min(batch_start + OCR_BATCH_SIZE, pages_to_ocr)
                try:
                    # Convert only the current batch of pages to images
                    batch_images = convert_from_bytes(
                        file_bytes,
                        dpi=150,  # Reduced from 200 to save memory
                        first_page=batch_start + 1,  # 1-indexed
                        last_page=batch_end
                    )
                    for image in batch_images:
                        try:
                            text = pytesseract.image_to_string(image)
                            if text and text.strip():
                                ocr_pages.append(text)
                        except Exception as ocr_err:
                            logger.warning(f"OCR failed for a page: {ocr_err}")
                        finally:
                            # Explicitly free image memory
                            image.close()
                    del batch_images
                except Exception as batch_err:
                    logger.warning(
                        f"OCR batch {batch_start+1}-{batch_end} failed: {batch_err}"
                    )
                    continue

            if ocr_pages:
                logger.info(f"OCR extracted text from {len(ocr_pages)} pages")
                return '\n\n'.join(ocr_pages)
        except ImportError:
            logger.warning("OCR packages (pytesseract/pdf2image) not installed, skipping OCR")
        except Exception as e:
            logger.warning(f"PDF OCR extraction failed: {e}")

        return ''

    elif file_type == 'docx':
        # Try python-docx first (handles .docx files)
        try:
            from docx import Document
            doc = Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = '\n\n'.join(paragraphs)
            if text.strip():
                return text
        except Exception:
            pass

        # Fallback: Use LibreOffice for legacy .doc files
        try:
            import subprocess
            import tempfile
            import os
            with tempfile.TemporaryDirectory() as tmp_dir:
                input_path = os.path.join(tmp_dir, 'input.doc')
                with open(input_path, 'wb') as f:
                    f.write(file_bytes)
                # Convert to plain text using LibreOffice
                subprocess.run(
                    ['libreoffice', '--headless', '--convert-to', 'txt:Text', '--outdir', tmp_dir, input_path],
                    capture_output=True, timeout=30
                )
                txt_path = os.path.join(tmp_dir, 'input.txt')
                if os.path.exists(txt_path):
                    with open(txt_path, 'r', encoding='utf-8', errors='replace') as f:
                        return f.read()
            logger.warning("LibreOffice DOC conversion produced no output")
            return ''
        except Exception as e:
            logger.warning(f"DOC/DOCX extraction failed: {e}")
            return ''

    elif file_type == 'pptx':
        # Try python-pptx first (handles .pptx files)
        try:
            from pptx import Presentation
            prs = Presentation(io.BytesIO(file_bytes))
            slides_text = []
            for slide in prs.slides:
                slide_parts = []
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for paragraph in shape.text_frame.paragraphs:
                            text = paragraph.text.strip()
                            if text:
                                slide_parts.append(text)
                if slide_parts:
                    slides_text.append('\n'.join(slide_parts))
            text = '\n\n'.join(slides_text)
            if text.strip():
                return text
        except Exception:
            pass

        # Fallback: Use LibreOffice for legacy .ppt files
        try:
            import subprocess
            import tempfile
            import os
            with tempfile.TemporaryDirectory() as tmp_dir:
                input_path = os.path.join(tmp_dir, 'input.ppt')
                with open(input_path, 'wb') as f:
                    f.write(file_bytes)
                subprocess.run(
                    ['libreoffice', '--headless', '--convert-to', 'txt:Text', '--outdir', tmp_dir, input_path],
                    capture_output=True, timeout=30
                )
                txt_path = os.path.join(tmp_dir, 'input.txt')
                if os.path.exists(txt_path):
                    with open(txt_path, 'r', encoding='utf-8', errors='replace') as f:
                        return f.read()
            logger.warning("LibreOffice PPT conversion produced no output")
            return ''
        except Exception as e:
            logger.warning(f"PPT/PPTX extraction failed: {e}")
            return ''

    elif file_type == 'csv':
        try:
            import csv as csv_module
            text_stream = io.StringIO(file_bytes.decode('utf-8', errors='replace'))
            reader = csv_module.reader(text_stream)
            rows = []
            for row in reader:
                rows.append(', '.join(row))
            return '\n'.join(rows)
        except Exception as e:
            logger.warning(f"CSV extraction failed: {e}")
            return ''

    elif file_type == 'xlsx':
        try:
            from openpyxl import load_workbook
            wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
            sheets_text = []
            for ws in wb.worksheets:
                rows = []
                for row in ws.iter_rows(values_only=True):
                    cell_values = [str(cell) if cell is not None else '' for cell in row]
                    row_text = ', '.join(v for v in cell_values if v)
                    if row_text:
                        rows.append(row_text)
                if rows:
                    sheets_text.append('\n'.join(rows))
            wb.close()
            return '\n\n'.join(sheets_text)
        except Exception as e:
            logger.warning(f"XLSX extraction failed: {e}")
            return ''

    return ''


def _get_file_type_from_extension(filename):
    """Map file extension to file_type choice."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    ext_map = {
        'pdf': 'pdf',
        'pptx': 'pptx',
        'ppt': 'pptx',
        'docx': 'docx',
        'doc': 'docx',
        'csv': 'csv',
        'xlsx': 'xlsx',
        'xls': 'xlsx',
    }
    return ext_map.get(ext)


def _create_document_chunks(document):
    """
    Split a ReferenceDocument's extracted_text into chunks and store them.
    Deletes any existing chunks first (for re-chunking on update).

    For large documents (>100K chars), uses larger chunk size (10K) to reduce
    chunk count and improve keyword filtering performance.
    """
    from domains.models import ReferenceDocumentChunk

    # Clear existing chunks
    document.chunks.all().delete()

    text = document.extracted_text or ''
    if not text.strip():
        return

    # Adaptive chunk size: larger chunks for large documents
    LARGE_DOC_THRESHOLD = 100000  # 100K characters
    if len(text) > LARGE_DOC_THRESHOLD:
        chunk_size = 10000  # 10K chars per chunk for large docs
        overlap = 400       # Proportionally larger overlap
    else:
        chunk_size = ReferenceDocumentChunk.CHUNK_SIZE   # 5K default
        overlap = ReferenceDocumentChunk.CHUNK_OVERLAP   # 200 default

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]

        if chunk_text.strip():
            chunks.append(ReferenceDocumentChunk(
                document=document,
                chunk_index=chunk_index,
                chunk_text=chunk_text
            ))
            chunk_index += 1

        # Move forward by (chunk_size - overlap) to maintain context continuity
        start += chunk_size - overlap

    if chunks:
        # Bulk create in batches to avoid memory issues with very large docs
        BATCH_SIZE = 100
        for i in range(0, len(chunks), BATCH_SIZE):
            ReferenceDocumentChunk.objects.bulk_create(chunks[i:i + BATCH_SIZE])

    logger.info(
        f"[CHUNKING] Document '{document.file_name}' (ID: {document.id}): "
        f"{len(text)} chars -> {len(chunks)} chunks "
        f"(chunk_size={chunk_size}, overlap={overlap})"
    )


def _async_extract_and_chunk(document_id, file_type):
    """
    Background thread function to extract text from large files and create chunks.
    Updates the document's extraction_status when done.
    Runs outside the HTTP request lifecycle for files >5MB.
    """
    import django
    django.setup()
    from domains.models import ReferenceDocument

    try:
        doc = ReferenceDocument.objects.get(id=document_id)
        logger.info(
            f"[ASYNC-EXTRACT] Starting background extraction for "
            f"'{doc.file_name}' (ID: {doc.id}, size: {doc.file_size} bytes)"
        )

        # Extract text from the saved file on disk
        extracted_text = ''
        if doc.file:
            try:
                with doc.file.open('rb') as f:
                    extracted_text = _extract_text_from_file(f, file_type)
            except Exception as e:
                logger.error(f"[ASYNC-EXTRACT] File read failed for doc {doc.id}: {e}")
                doc.extraction_status = 'failed'
                doc.extraction_error = f"Failed to read file: {str(e)}"
                doc.save(update_fields=['extraction_status', 'extraction_error'])
                return

        if not extracted_text:
            logger.warning(
                f"[ASYNC-EXTRACT] No text extracted from '{doc.file_name}' ({file_type})"
            )

        # Update the document with extracted text
        doc.extracted_text = extracted_text
        doc.extraction_status = 'completed'
        doc.extraction_error = ''
        doc.save(update_fields=['extracted_text', 'extraction_status', 'extraction_error'])

        # Create chunks
        _create_document_chunks(doc)

        logger.info(
            f"[ASYNC-EXTRACT] Completed extraction for '{doc.file_name}' "
            f"(ID: {doc.id}): {len(extracted_text)} chars extracted"
        )
    except ReferenceDocument.DoesNotExist:
        logger.error(f"[ASYNC-EXTRACT] Document {document_id} not found (may have been deleted)")
    except Exception as e:
        logger.error(f"[ASYNC-EXTRACT] Unexpected error for doc {document_id}: {e}")
        try:
            doc = ReferenceDocument.objects.get(id=document_id)
            doc.extraction_status = 'failed'
            doc.extraction_error = str(e)[:500]
            doc.save(update_fields=['extraction_status', 'extraction_error'])
        except Exception:
            pass


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def reference_document_list(request, domain_id):
    """
    GET: List all reference documents for a domain
    POST: Upload a file or add a text note
    """
    try:
        domain = Domain.objects.get(id=domain_id, organisation=request.user.organisation)
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found or not in your organization'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        docs = ReferenceDocument.objects.filter(domain=domain)
        serializer = ReferenceDocumentSerializer(docs, many=True, context={'request': request})
        total_size = sum(d.file_size for d in docs)
        return Response({
            'reference_documents': serializer.data,
            'total_files': docs.count(),
            'total_size_bytes': total_size,
            'max_files': ReferenceDocument.MAX_FILES_PER_DOMAIN,
        })

    # POST - Upload file or add text note
    current_count = ReferenceDocument.objects.filter(domain=domain).count()
    if current_count >= ReferenceDocument.MAX_FILES_PER_DOMAIN:
        return Response(
            {'error': f'Maximum {ReferenceDocument.MAX_FILES_PER_DOMAIN} reference documents per domain'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if this is a text note
    if request.data.get('file_type') == 'text':
        text_content = request.data.get('text_content', '').strip()
        title = request.data.get('title', 'Text Note').strip()
        description = request.data.get('description', '').strip()

        if not text_content:
            return Response(
                {'error': 'text_content is required for text notes'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(text_content) > ReferenceDocument.MAX_TEXT_LENGTH:
            return Response(
                {'error': f'Text content exceeds maximum length of {ReferenceDocument.MAX_TEXT_LENGTH} characters'},
                status=status.HTTP_400_BAD_REQUEST
            )

        doc = ReferenceDocument.objects.create(
            domain=domain,
            file_name=title,
            file_type='text',
            file_size=0,
            extracted_text=text_content,
            description=description,
            uploaded_by=request.user,
        )
        _create_document_chunks(doc)
        serializer = ReferenceDocumentSerializer(doc, context={'request': request})
        return Response({
            'message': 'Text note added successfully',
            'reference_document': serializer.data
        }, status=status.HTTP_201_CREATED)

    # File upload
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return Response(
            {'error': 'No file provided. Send a file or set file_type=text for text notes'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Determine file type from extension
    file_type = _get_file_type_from_extension(uploaded_file.name)
    if not file_type:
        return Response(
            {'error': 'Unsupported file type. Allowed: PDF, PPT/PPTX, DOC/DOCX, CSV, XLS/XLSX'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check file size limit
    max_size = ReferenceDocument.MAX_FILE_SIZES.get(file_type, 5 * 1024 * 1024)
    if uploaded_file.size > max_size:
        max_mb = max_size / (1024 * 1024)
        return Response(
            {'error': f'File too large. Maximum size for {file_type.upper()} is {max_mb:.0f} MB'},
            status=status.HTTP_400_BAD_REQUEST
        )

    description = request.data.get('description', '').strip()

    # For large files (>5MB), process extraction asynchronously in background
    ASYNC_THRESHOLD = 5 * 1024 * 1024  # 5MB

    if uploaded_file.size > ASYNC_THRESHOLD:
        # Save document immediately with 'processing' status
        doc = ReferenceDocument.objects.create(
            domain=domain,
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_type=file_type,
            file_size=uploaded_file.size,
            extracted_text='',
            extraction_status='processing',
            description=description,
            uploaded_by=request.user,
        )

        # Run extraction in background thread
        import threading
        thread = threading.Thread(
            target=_async_extract_and_chunk,
            args=(doc.id, file_type),
            daemon=True
        )
        thread.start()

        serializer = ReferenceDocumentSerializer(doc, context={'request': request})
        return Response({
            'message': 'File uploaded successfully. Text extraction is processing in the background for this large file.',
            'reference_document': serializer.data,
            'extraction_status': 'processing'
        }, status=status.HTTP_201_CREATED)
    else:
        # Small files — extract synchronously (fast, no delay)
        extracted_text = _extract_text_from_file(uploaded_file, file_type)
        if not extracted_text:
            logger.warning(f"No text extracted from {uploaded_file.name} ({file_type})")

        doc = ReferenceDocument.objects.create(
            domain=domain,
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_type=file_type,
            file_size=uploaded_file.size,
            extracted_text=extracted_text,
            extraction_status='completed',
            description=description,
            uploaded_by=request.user,
        )
        _create_document_chunks(doc)

        serializer = ReferenceDocumentSerializer(doc, context={'request': request})
        return Response({
            'message': 'File uploaded successfully',
            'reference_document': serializer.data,
            'extraction_status': 'completed'
        }, status=status.HTTP_201_CREATED)


@api_view(['GET', 'DELETE', 'PATCH'])
@permission_classes([IsAuthenticated])
def reference_document_detail(request, domain_id, doc_id):
    """
    GET: Get single reference document details
    DELETE: Remove a reference document
    PATCH: Update text note content or description
    """
    try:
        domain = Domain.objects.get(id=domain_id, organisation=request.user.organisation)
        doc = ReferenceDocument.objects.get(id=doc_id, domain=domain)
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found or not in your organization'},
            status=status.HTTP_404_NOT_FOUND
        )
    except ReferenceDocument.DoesNotExist:
        return Response(
            {'error': 'Reference document not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        serializer = ReferenceDocumentSerializer(doc, context={'request': request})
        return Response({'reference_document': serializer.data})

    if request.method == 'DELETE':
        # Delete the physical file if it exists
        if doc.file:
            try:
                doc.file.delete(save=False)
            except Exception as e:
                logger.warning(f"Failed to delete file for reference doc {doc.id}: {e}")
        doc.delete()
        return Response({'message': 'Reference document deleted successfully'})

    # PATCH - Update text note or description
    if request.method == 'PATCH':
        if doc.file_type == 'text':
            text_content = request.data.get('text_content')
            if text_content is not None:
                text_content = text_content.strip()
                if len(text_content) > ReferenceDocument.MAX_TEXT_LENGTH:
                    return Response(
                        {'error': f'Text content exceeds maximum length of {ReferenceDocument.MAX_TEXT_LENGTH} characters'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                doc.extracted_text = text_content

            title = request.data.get('title')
            if title is not None:
                doc.file_name = title.strip()

        description = request.data.get('description')
        if description is not None:
            doc.description = description.strip()

        doc.save()
        # Re-chunk if text content was updated
        if doc.file_type == 'text' and request.data.get('text_content') is not None:
            _create_document_chunks(doc)
        serializer = ReferenceDocumentSerializer(doc, context={'request': request})
        return Response({
            'message': 'Reference document updated successfully',
            'reference_document': serializer.data
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reference_document_extraction_status(request, domain_id, doc_id):
    """
    GET: Check the extraction status of a reference document.
    Used by frontend to poll for completion of async extraction on large files.
    """
    try:
        domain = Domain.objects.get(id=domain_id, organisation=request.user.organisation)
        doc = ReferenceDocument.objects.get(id=doc_id, domain=domain)
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found or not in your organization'},
            status=status.HTTP_404_NOT_FOUND
        )
    except ReferenceDocument.DoesNotExist:
        return Response(
            {'error': 'Reference document not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    extracted_chars = len(doc.extracted_text) if doc.extracted_text else 0
    chunk_count = doc.chunks.count()

    return Response({
        'extraction_status': doc.extraction_status,
        'extraction_error': doc.extraction_error,
        'extracted_chars': extracted_chars,
        'chunk_count': chunk_count,
    })


# ===== Brand Links =====

def _create_brand_link_chunks(brand_link):
    """
    Split a BrandLink's extracted_text into chunks and store them.
    Same chunking strategy as reference documents.
    """
    brand_link.chunks.all().delete()

    text = brand_link.extracted_text or ''
    if not text.strip():
        return

    LARGE_DOC_THRESHOLD = 100000
    if len(text) > LARGE_DOC_THRESHOLD:
        chunk_size = 10000
        overlap = 400
    else:
        chunk_size = BrandLinkChunk.CHUNK_SIZE
        overlap = BrandLinkChunk.CHUNK_OVERLAP

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]

        if chunk_text.strip():
            chunks.append(BrandLinkChunk(
                brand_link=brand_link,
                chunk_index=chunk_index,
                chunk_text=chunk_text
            ))
            chunk_index += 1

        start += chunk_size - overlap

    if chunks:
        BATCH_SIZE = 100
        for i in range(0, len(chunks), BATCH_SIZE):
            BrandLinkChunk.objects.bulk_create(chunks[i:i + BATCH_SIZE])

    logger.info(
        f"[CHUNKING] BrandLink '{brand_link.url}' (ID: {brand_link.id}): "
        f"{len(text)} chars -> {len(chunks)} chunks "
        f"(chunk_size={chunk_size}, overlap={overlap})"
    )


# Real browser User-Agent — sites block "bot" UAs
_BROWSER_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Facebook's external scraper UA — whitelisted by Facebook, Instagram,
# LinkedIn and most major sites for OG metadata extraction.
_FB_EXTERNAL_UA = 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)'

# Slackbot UA — whitelisted by Medium, Substack, and many publications
# that block other scrapers but allow link unfurling.
_SLACKBOT_UA = 'Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)'

# Twitterbot UA — also whitelisted by many sites for OG metadata
_TWITTERBOT_UA = 'Twitterbot/1.0'

# Minimum content length below which we consider extraction to have produced
# insufficient content and trigger a fallback strategy.
_MIN_USEFUL_CONTENT = 200


def _build_browser_headers(ua=None):
    """Real browser headers that minimize bot blocking."""
    return {
        'User-Agent': ua or _BROWSER_UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }


def _extract_meta_from_html(html):
    """
    Extract Open Graph and standard meta tags from HTML.
    Returns a dict with title, description, site_name, keywords, etc.
    Works for almost every website since OG tags are universal for sharing.
    """
    from bs4 import BeautifulSoup

    info = {}
    try:
        soup = BeautifulSoup(html, 'html.parser')

        if soup.title and soup.title.string:
            info['title'] = soup.title.string.strip()

        for meta in soup.find_all('meta'):
            prop = meta.get('property') or meta.get('name')
            content = meta.get('content')
            if not prop or not content:
                continue
            prop = prop.lower().strip()
            content = content.strip()

            if prop == 'description':
                info.setdefault('description', content)
            elif prop == 'keywords':
                info['keywords'] = content
            elif prop == 'author':
                info['author'] = content
            elif prop == 'og:title':
                info['og_title'] = content
            elif prop == 'og:description':
                info['og_description'] = content
            elif prop == 'og:site_name':
                info['site_name'] = content
            elif prop == 'og:type':
                info['og_type'] = content
            elif prop == 'og:url':
                info['og_url'] = content
            elif prop == 'twitter:title':
                info['twitter_title'] = content
            elif prop == 'twitter:description':
                info['twitter_description'] = content
            elif prop == 'twitter:creator':
                info['twitter_creator'] = content

        # Also pull JSON-LD structured data (YouTube, blogs, etc. expose it here)
        jsonld_texts = []
        for script in soup.find_all('script', {'type': 'application/ld+json'}):
            try:
                import json as _json
                data = _json.loads(script.string or '{}')
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    for key in ('name', 'headline', 'description', 'about', 'articleBody'):
                        val = item.get(key)
                        if isinstance(val, str) and val.strip():
                            jsonld_texts.append(f"{key}: {val.strip()}")
            except Exception:
                continue
        if jsonld_texts:
            info['jsonld'] = '\n'.join(jsonld_texts)

    except Exception as e:
        logger.warning(f"[BRAND-LINK-CRAWL] Meta extraction failed: {e}")

    return info


def _format_meta_section(meta):
    """Format meta info dict into a readable text section."""
    lines = []
    if meta.get('title'):
        lines.append(f"Title: {meta['title']}")
    if meta.get('og_title') and meta.get('og_title') != meta.get('title'):
        lines.append(f"OG Title: {meta['og_title']}")
    if meta.get('site_name'):
        lines.append(f"Site: {meta['site_name']}")
    if meta.get('author'):
        lines.append(f"Author: {meta['author']}")
    if meta.get('twitter_creator'):
        lines.append(f"Twitter: {meta['twitter_creator']}")

    # Pick the longest description — Instagram, Facebook etc. sometimes
    # have a richer bio in the standard meta description than in og:description.
    descriptions = [
        meta.get('og_description', ''),
        meta.get('description', ''),
        meta.get('twitter_description', ''),
    ]
    description = max(descriptions, key=len) if any(descriptions) else ''
    if description:
        lines.append(f"Description: {description}")

    if meta.get('keywords'):
        lines.append(f"Keywords: {meta['keywords']}")

    if meta.get('jsonld'):
        lines.append(f"\nStructured Data:\n{meta['jsonld']}")

    return '\n'.join(lines)


def _extract_main_text_from_html(html):
    """
    Extract main content text from HTML using trafilatura with BeautifulSoup fallback.
    """
    main_text = None

    # Strategy 1: trafilatura (better at finding main article/content)
    try:
        import trafilatura
        main_text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
        )
    except Exception as e:
        logger.warning(f"[BRAND-LINK-CRAWL] trafilatura extraction failed: {e}")

    # Strategy 2: BeautifulSoup fallback
    if not main_text or len(main_text.strip()) < 50:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'iframe', 'noscript']):
                element.decompose()
            main_text = soup.get_text(separator='\n', strip=True)
            import re
            main_text = re.sub(r'\n{3,}', '\n\n', main_text).strip()
        except Exception as e:
            logger.warning(f"[BRAND-LINK-CRAWL] BeautifulSoup fallback failed: {e}")

    return main_text or ''


def _fetch_with_browser(url, timeout=20, ua=None):
    """Direct fetch with browser headers. Returns HTML or None on failure."""
    import requests
    try:
        resp = requests.get(url, headers=_build_browser_headers(ua=ua), timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.info(f"[BRAND-LINK-CRAWL] Direct fetch failed for {url}: {e}")
        return None


def _fetch_with_scrapingdog(url, dynamic=True):
    """
    Fallback fetch using ScrapingDog API for sites that block direct scrapers.
    Required for Twitter/X, Instagram, Facebook which use heavy JS or block bots.
    Returns HTML or None on failure.
    """
    try:
        from misinformation.services.crawler import WebCrawler
        crawler = WebCrawler(use_dynamic=dynamic)
        if not crawler.api_key:
            logger.warning("[BRAND-LINK-CRAWL] SCRAPINGDOG_API_KEY not configured — cannot use fallback")
            return None
        html, status_code, error = crawler.crawl(url, dynamic=dynamic)
        if html:
            logger.info(f"[BRAND-LINK-CRAWL] ScrapingDog succeeded for {url} ({len(html)} chars)")
            return html
        logger.info(f"[BRAND-LINK-CRAWL] ScrapingDog failed for {url}: status={status_code}, error={error}")
    except Exception as e:
        logger.warning(f"[BRAND-LINK-CRAWL] ScrapingDog fallback error for {url}: {e}")
    return None


def _extract_youtube_content(url):
    """
    YouTube content extraction:
    1. Use public oEmbed API (no auth, always works) — title, channel
    2. Fetch the watch page for description, keywords, and metadata
    """
    import requests
    parts = []

    # 1. oEmbed API — works without authentication
    try:
        oembed_url = f'https://www.youtube.com/oembed?url={url}&format=json'
        resp = requests.get(oembed_url, headers=_build_browser_headers(), timeout=15)
        if resp.ok:
            data = resp.json()
            if data.get('title'):
                parts.append(f"Video Title: {data['title']}")
            if data.get('author_name'):
                parts.append(f"Channel: {data['author_name']}")
            if data.get('author_url'):
                parts.append(f"Channel URL: {data['author_url']}")
            if data.get('provider_name'):
                parts.append(f"Provider: {data['provider_name']}")
    except Exception as e:
        logger.warning(f"[BRAND-LINK-CRAWL] YouTube oEmbed failed: {e}")

    # 2. Fetch the watch page for full metadata (description, keywords, etc.)
    html = _fetch_with_browser(url, timeout=20)
    if html:
        meta = _extract_meta_from_html(html)
        meta_text = _format_meta_section(meta)
        if meta_text:
            parts.append("")
            parts.append("--- Page Metadata ---")
            parts.append(meta_text)

    if not parts:
        # Last-resort fallback via ScrapingDog
        html = _fetch_with_scrapingdog(url, dynamic=True)
        if html:
            meta = _extract_meta_from_html(html)
            meta_text = _format_meta_section(meta)
            if meta_text:
                parts.append(meta_text)

    return '\n'.join(parts).strip()


def _extract_twitter_content(url):
    """
    Twitter/X content extraction.
    Strategy:
    1. Use community fxtwitter API for profiles (free, no auth) — returns JSON
       with name, description, location, follower counts, etc.
    2. For tweet URLs, fxtwitter also returns tweet text and metadata.
    3. Fall back to direct browser fetch + OG tags if fxtwitter fails.
    """
    import requests
    import re

    parts = []

    # Parse username and optional tweet ID from URL
    # Supports both twitter.com and x.com
    username = None
    tweet_id = None
    m = re.match(r'https?://(?:www\.)?(?:twitter|x)\.com/([^/?#]+)(?:/status/(\d+))?', url)
    if m:
        username = m.group(1)
        tweet_id = m.group(2)

    # 1. Try fxtwitter API
    if username:
        try:
            api_url = f'https://api.fxtwitter.com/{username}'
            if tweet_id:
                api_url = f'https://api.fxtwitter.com/{username}/status/{tweet_id}'
            r = requests.get(api_url, headers={'User-Agent': _BROWSER_UA}, timeout=15)
            if r.ok:
                data = r.json()
                if tweet_id and data.get('tweet'):
                    tw = data['tweet']
                    if tw.get('author', {}).get('name'):
                        parts.append(f"Author: {tw['author']['name']} (@{tw['author'].get('screen_name', username)})")
                    if tw.get('author', {}).get('description'):
                        parts.append(f"Author Bio: {tw['author']['description']}")
                    if tw.get('text'):
                        parts.append(f"\nTweet: {tw['text']}")
                    if tw.get('created_at'):
                        parts.append(f"Posted: {tw['created_at']}")
                    if tw.get('likes') is not None:
                        parts.append(f"Likes: {tw['likes']}, Retweets: {tw.get('retweets', 0)}, Replies: {tw.get('replies', 0)}")
                elif data.get('user'):
                    user = data['user']
                    if user.get('name'):
                        parts.append(f"Name: {user['name']}")
                    if user.get('screen_name'):
                        parts.append(f"Handle: @{user['screen_name']}")
                    if user.get('description'):
                        parts.append(f"Bio: {user['description']}")
                    if user.get('location'):
                        parts.append(f"Location: {user['location']}")
                    if user.get('followers') is not None:
                        parts.append(f"Followers: {user['followers']}, Following: {user.get('following', 0)}, Tweets: {user.get('tweets', 0)}")
                    if user.get('url'):
                        parts.append(f"Profile URL: {user['url']}")
        except Exception as e:
            logger.warning(f"[BRAND-LINK-CRAWL] fxtwitter API failed for {url}: {e}")

    # 2. Fall back to vxtwitter if fxtwitter returned nothing
    if not parts and username:
        try:
            api_url = f'https://api.vxtwitter.com/{username}'
            r = requests.get(api_url, headers={'User-Agent': _BROWSER_UA}, timeout=15)
            if r.ok:
                data = r.json()
                if data.get('name'):
                    parts.append(f"Name: {data['name']}")
                if data.get('screen_name'):
                    parts.append(f"Handle: @{data['screen_name']}")
                if data.get('description'):
                    parts.append(f"Bio: {data['description']}")
                if data.get('location'):
                    parts.append(f"Location: {data['location']}")
                if data.get('followers_count') is not None:
                    parts.append(f"Followers: {data['followers_count']}, Following: {data.get('following_count', 0)}")
                if data.get('tweet_count') is not None:
                    parts.append(f"Tweets: {data['tweet_count']}")
        except Exception as e:
            logger.warning(f"[BRAND-LINK-CRAWL] vxtwitter API failed for {url}: {e}")

    # 3. Final fallback: direct fetch for whatever OG tags we can get
    if not parts:
        html = _fetch_with_browser(url, timeout=15)
        if html:
            meta = _extract_meta_from_html(html)
            meta_text = _format_meta_section(meta)
            if meta_text:
                parts.append(meta_text)

    return '\n'.join(parts).strip()


def _extract_meta_social_content(url):
    """
    Extract content from Facebook, Instagram, and LinkedIn.
    Strategy: Use facebookexternalhit/1.1 user agent — these sites whitelist
    Facebook's crawler bot for OG metadata sharing previews.
    """
    parts = []

    # 1. Fetch with facebookexternalhit UA (works for FB, IG, LinkedIn)
    html = _fetch_with_browser(url, timeout=20, ua=_FB_EXTERNAL_UA)

    # 2. Fall back to standard browser UA if FB UA failed
    if not html:
        html = _fetch_with_browser(url, timeout=20)

    if html:
        meta = _extract_meta_from_html(html)
        meta_text = _format_meta_section(meta)
        if meta_text:
            parts.append(meta_text)

        # Also try to extract any visible page text
        main_text = _extract_main_text_from_html(html)
        if main_text and len(main_text.strip()) >= 50:
            # Trim very long pages — social pages often have lots of boilerplate
            if len(main_text) > 8000:
                main_text = main_text[:8000] + '\n...[content truncated]...'
            parts.append("")
            parts.append("--- Page Content ---")
            parts.append(main_text)

    return '\n'.join(parts).strip()


def _extract_general_content(url):
    """
    Extract content from general websites (blogs, microsites, other).
    Tries multiple user agents in order — sites like Medium, Substack and
    many publications block standard scrapers but whitelist link-unfurling
    bots like Slackbot, Twitterbot, and facebookexternalhit.
    """
    parts = []

    # Try a series of UAs that are commonly whitelisted
    ua_strategies = [
        (None, 'browser'),               # Default Chrome UA
        (_SLACKBOT_UA, 'slackbot'),      # Works for Medium, Substack
        (_FB_EXTERNAL_UA, 'fb-external'),# Works for Facebook, IG, many publishers
        (_TWITTERBOT_UA, 'twitterbot'),  # Works for many news sites
    ]

    html = None
    for ua, label in ua_strategies:
        html = _fetch_with_browser(url, timeout=20, ua=ua)
        if html and len(html) > 1000:
            logger.info(f"[BRAND-LINK-CRAWL] Got content via {label} UA for {url}")
            break

    # Fallback to ScrapingDog if all UAs failed
    if not html:
        html = _fetch_with_scrapingdog(url, dynamic=False)

    # Try with dynamic rendering as last resort
    if not html:
        html = _fetch_with_scrapingdog(url, dynamic=True)

    if not html:
        return ''

    # Extract meta info first
    meta = _extract_meta_from_html(html)
    meta_text = _format_meta_section(meta)
    if meta_text:
        parts.append(meta_text)

    # Then extract main page content
    main_text = _extract_main_text_from_html(html)
    if main_text:
        parts.append("")
        parts.append("--- Page Content ---")
        parts.append(main_text)

    return '\n'.join(parts).strip()


def _extract_brand_link_content(url, platform):
    """
    Dispatch to platform-specific extractor for best results.
    Returns the extracted text or empty string.
    """
    platform = (platform or '').lower()

    if platform == 'youtube':
        return _extract_youtube_content(url)
    if platform == 'twitter':
        return _extract_twitter_content(url)
    if platform in ('facebook', 'instagram', 'linkedin'):
        return _extract_meta_social_content(url)
    # blog, microsite, other
    return _extract_general_content(url)


def _async_crawl_and_chunk_brand_link(brand_link_id):
    """
    Background thread function to crawl a brand link URL, extract text,
    and create chunks. Uses a platform-aware extractor with multiple
    fallback strategies (direct fetch, ScrapingDog, oEmbed for YouTube).
    """
    import django
    django.setup()
    from domains.models import BrandLink as BrandLinkModel

    try:
        link = BrandLinkModel.objects.get(id=brand_link_id)
        logger.info(
            f"[BRAND-LINK-CRAWL] Starting crawl for '{link.url}' "
            f"(ID: {link.id}, platform: {link.platform})"
        )

        link.extraction_status = 'processing'
        link.save(update_fields=['extraction_status'])

        try:
            extracted_text = _extract_brand_link_content(link.url, link.platform)
        except Exception as e:
            logger.error(f"[BRAND-LINK-CRAWL] Extractor crashed for '{link.url}': {e}")
            link.extraction_status = 'failed'
            link.extraction_error = f"Extraction error: {str(e)[:300]}"
            link.save(update_fields=['extraction_status', 'extraction_error'])
            return

        if not extracted_text or not extracted_text.strip():
            link.extraction_status = 'failed'
            link.extraction_error = (
                'Could not extract any content from this URL. The site may be '
                'blocking automated access or require login. Try adding the '
                'content manually as a Text Note in Reference Documents.'
            )
            link.save(update_fields=['extraction_status', 'extraction_error'])
            return

        link.extracted_text = extracted_text
        link.extraction_status = 'completed'
        link.extraction_error = ''
        link.save(update_fields=['extracted_text', 'extraction_status', 'extraction_error'])

        _create_brand_link_chunks(link)

        logger.info(
            f"[BRAND-LINK-CRAWL] Completed crawl for '{link.url}' "
            f"(ID: {link.id}): {len(extracted_text)} chars extracted"
        )

    except BrandLinkModel.DoesNotExist:
        logger.error(f"[BRAND-LINK-CRAWL] BrandLink {brand_link_id} not found")
    except Exception as e:
        logger.error(f"[BRAND-LINK-CRAWL] Unexpected error for brand link {brand_link_id}: {e}")
        try:
            link = BrandLinkModel.objects.get(id=brand_link_id)
            link.extraction_status = 'failed'
            link.extraction_error = str(e)[:500]
            link.save(update_fields=['extraction_status', 'extraction_error'])
        except Exception:
            pass


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def brand_link_list(request, domain_id):
    """
    GET: List all brand links for a domain
    POST: Add a new brand link
    """
    try:
        domain = Domain.objects.get(id=domain_id, organisation=request.user.organisation)
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found or not in your organization'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        links = BrandLink.objects.filter(domain=domain)
        serializer = BrandLinkSerializer(links, many=True, context={'request': request})
        return Response({
            'brand_links': serializer.data,
            'total_links': links.count(),
            'max_links': BrandLink.MAX_LINKS_PER_DOMAIN,
        })

    # POST - Add new brand link
    current_count = BrandLink.objects.filter(domain=domain).count()
    if current_count >= BrandLink.MAX_LINKS_PER_DOMAIN:
        return Response(
            {'error': f'Maximum {BrandLink.MAX_LINKS_PER_DOMAIN} brand links per domain'},
            status=status.HTTP_400_BAD_REQUEST
        )

    platform = request.data.get('platform', '').strip()
    url = request.data.get('url', '').strip()
    label = request.data.get('label', '').strip()

    if not platform:
        return Response(
            {'error': 'Platform is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    valid_platforms = [c[0] for c in BrandLink.PLATFORM_CHOICES]
    if platform not in valid_platforms:
        return Response(
            {'error': f'Invalid platform. Choose from: {", ".join(valid_platforms)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not url:
        return Response(
            {'error': 'URL is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not url.startswith(('http://', 'https://')):
        return Response(
            {'error': 'URL must start with http:// or https://'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check for duplicate URL within domain
    if BrandLink.objects.filter(domain=domain, url=url).exists():
        return Response(
            {'error': 'This URL is already added for this domain'},
            status=status.HTTP_400_BAD_REQUEST
        )

    link = BrandLink.objects.create(
        domain=domain,
        platform=platform,
        url=url,
        label=label,
        extraction_status='pending',
        added_by=request.user,
    )

    # Start background crawl
    import threading
    thread = threading.Thread(
        target=_async_crawl_and_chunk_brand_link,
        args=(link.id,),
        daemon=True
    )
    thread.start()

    serializer = BrandLinkSerializer(link, context={'request': request})
    return Response({
        'message': 'Brand link added successfully. Content extraction is processing in the background.',
        'brand_link': serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(['GET', 'DELETE', 'PATCH'])
@permission_classes([IsAuthenticated])
def brand_link_detail(request, domain_id, link_id):
    """
    GET: Get single brand link details (including extracted content)
    DELETE: Remove a brand link
    PATCH: Update a brand link
    """
    try:
        domain = Domain.objects.get(id=domain_id, organisation=request.user.organisation)
        link = BrandLink.objects.get(id=link_id, domain=domain)
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found or not in your organization'},
            status=status.HTTP_404_NOT_FOUND
        )
    except BrandLink.DoesNotExist:
        return Response(
            {'error': 'Brand link not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        serializer = BrandLinkSerializer(link, context={'request': request})
        return Response({'brand_link': serializer.data})

    if request.method == 'DELETE':
        link.delete()
        return Response({'message': 'Brand link deleted successfully'})

    # PATCH - Update brand link
    if request.method == 'PATCH':
        label = request.data.get('label')
        if label is not None:
            link.label = label.strip()

        platform = request.data.get('platform')
        if platform is not None:
            valid_platforms = [c[0] for c in BrandLink.PLATFORM_CHOICES]
            if platform not in valid_platforms:
                return Response(
                    {'error': f'Invalid platform. Choose from: {", ".join(valid_platforms)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            link.platform = platform

        link.save()
        serializer = BrandLinkSerializer(link, context={'request': request})
        return Response({
            'message': 'Brand link updated successfully',
            'brand_link': serializer.data
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def brand_link_recrawl(request, domain_id, link_id):
    """
    POST: Re-crawl a brand link to refresh extracted content
    """
    try:
        domain = Domain.objects.get(id=domain_id, organisation=request.user.organisation)
        link = BrandLink.objects.get(id=link_id, domain=domain)
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found or not in your organization'},
            status=status.HTTP_404_NOT_FOUND
        )
    except BrandLink.DoesNotExist:
        return Response(
            {'error': 'Brand link not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if link.extraction_status == 'processing':
        return Response(
            {'error': 'Extraction is already in progress'},
            status=status.HTTP_400_BAD_REQUEST
        )

    link.extraction_status = 'pending'
    link.extraction_error = ''
    link.save(update_fields=['extraction_status', 'extraction_error'])

    import threading
    thread = threading.Thread(
        target=_async_crawl_and_chunk_brand_link,
        args=(link.id,),
        daemon=True
    )
    thread.start()

    serializer = BrandLinkSerializer(link, context={'request': request})
    return Response({
        'message': 'Re-crawling brand link in the background.',
        'brand_link': serializer.data
    })