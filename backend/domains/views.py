from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction, connection
from django.db import IntegrityError
from django.db.utils import ProgrammingError
from django.conf import settings
from .models import Domain, DomainAccess
from .serializers import (
    DomainSerializer, DomainDetailSerializer,
    DomainAccessSerializer, DomainAccessCreateSerializer
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
        genai.configure(api_key=api_key)
        return genai
    except Exception as e:
        raise Exception(f"Failed to initialize Google GenAI client: {e}")


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def domain_list(request):
    """List all domains for the organization or create a new one"""
    if request.method == 'GET':
        # Optional management scope: allow admins to fetch all org domains when managing access
        manage_scope = request.query_params.get('manage') in ['1', 'true', 'True']
        # Filter domains by organization and user access
        if request.user.role == 'super_admin' or (request.user.role == 'admin' and manage_scope):
            # Super admins see all; admins see all when managing
            domains = Domain.objects.filter(organisation=request.user.organisation)
        else:
            # Admins and users can only see domains they have explicit access to
            domain_ids = DomainAccess.objects.filter(
                user=request.user,
                domain__organisation=request.user.organisation
            ).values_list('domain_id', flat=True)
            domains = Domain.objects.filter(id__in=domain_ids)
        
        serializer = DomainSerializer(domains, many=True)
        return Response({
            'domains': serializer.data
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
        if request.user.role == 'super_admin':
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
        if request.user.role == 'super_admin':
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
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organization administrators can manage domain access'}, status=status.HTTP_403_FORBIDDEN)
    try:
        domain = Domain.objects.get(id=domain_id, organisation=request.user.organisation)
    except Domain.DoesNotExist:
        return Response({'error': 'Domain not found or not in your organization'}, status=status.HTTP_404_NOT_FOUND)

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
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organization administrators can manage domain access'}, status=status.HTTP_403_FORBIDDEN)
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
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        prompt = f"""Analyze the brand "{brand_name}" (website: {domain_name}) and suggest relevant industry niches or categories.

Return ONLY a JSON array of 5-8 specific industry niches/categories that best describe this brand's market positioning. Each niche should be:
- Specific and descriptive (e.g., "Enterprise Cloud Security Solutions" not just "Security")
- Industry-relevant
- Useful for market positioning and competitive analysis

Example format:
["Enterprise SaaS", "Cloud Infrastructure", "DevOps Tools", "IT Security", "Business Intelligence"]

Provide the response as a valid JSON array only, no additional text."""

        response = model.generate_content(prompt)
        result_text = response.text.strip()

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
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

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

        response = model.generate_content(prompt)
        result_text = response.text.strip()

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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def domain_health_check(request, domain_id):
    """
    Perform comprehensive health checks on a domain to assess AI-friendliness
    Uses ScrapingDog API for reliable web scraping
    Checks: HTTPS, robots.txt, sitemap, meta tags, schema markup, content structure
    """
    import requests
    from urllib.parse import urljoin, urlparse
    import time
    import re

    try:
        domain = get_object_or_404(Domain, id=domain_id)
        url = domain.url

        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        health_score = 0
        max_score = 100
        checks = []

        # 1. HTTPS Check (10 points)
        https_check = {
            'name': 'HTTPS/SSL Certificate',
            'status': 'pass' if url.startswith('https://') else 'fail',
            'score': 10 if url.startswith('https://') else 0,
            'max_score': 10,
            'message': 'Website uses HTTPS' if url.startswith('https://') else 'Website should use HTTPS for security',
            'importance': 'high'
        }
        checks.append(https_check)
        health_score += https_check['score']

        # Get ScrapingDog API key from settings (optional, will fallback to direct request)
        scrapingdog_api_key = getattr(settings, "SCRAPINGDOG_API_KEY", None)

        # Fetch the homepage using ScrapingDog (with fallback to direct request)
        try:
            start_time = time.time()
            html_content = None

            # Try ScrapingDog first if API key is available
            if scrapingdog_api_key:
                try:
                    scrapingdog_url = "https://api.scrapingdog.com/scrape"
                    params = {
                        'api_key': scrapingdog_api_key,
                        'url': url,
                        'dynamic': 'false'
                    }

                    scrapingdog_response = requests.get(scrapingdog_url, params=params, timeout=30)

                    if scrapingdog_response.status_code == 200:
                        html_content = scrapingdog_response.text
                        logger.info(f"Successfully fetched {url} using ScrapingDog")
                    elif scrapingdog_response.status_code == 403:
                        logger.warning(f"ScrapingDog API returned 403 - API key might be invalid or quota exceeded. Falling back to direct request.")
                    else:
                        logger.warning(f"ScrapingDog returned status {scrapingdog_response.status_code}. Falling back to direct request.")
                except Exception as sd_error:
                    logger.warning(f"ScrapingDog error: {str(sd_error)}. Falling back to direct request.")

            # Fallback to direct request if ScrapingDog failed or not configured
            if not html_content:
                response = requests.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }, timeout=30)
                html_content = response.text
                logger.info(f"Successfully fetched {url} using direct request")

            load_time = time.time() - start_time

            # 2. Page Load Speed (10 points)
            speed_score = 10 if load_time < 3 else (5 if load_time < 6 else 0)
            speed_check = {
                'name': 'Page Load Speed',
                'status': 'pass' if load_time < 3 else ('warning' if load_time < 6 else 'fail'),
                'score': speed_score,
                'max_score': 10,
                'message': f'Page loads in {load_time:.2f}s' + (' (Excellent)' if load_time < 3 else ' (Needs improvement)'),
                'importance': 'medium'
            }
            checks.append(speed_check)
            health_score += speed_score

            # Parse HTML using regex for basic checks (no BeautifulSoup needed)

            # 3. Meta Title (10 points)
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
            title_text = title_match.group(1).strip() if title_match else None
            title_check = {
                'name': 'Meta Title Tag',
                'status': 'pass' if title_text and len(title_text) > 0 else 'fail',
                'score': 10 if (title_text and len(title_text) > 0) else 0,
                'max_score': 10,
                'message': f'Title: "{title_text[:60]}..."' if title_text else 'Missing title tag',
                'importance': 'high'
            }
            checks.append(title_check)
            health_score += title_check['score']

            # 4. Meta Description (10 points)
            meta_desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html_content, re.IGNORECASE)
            if not meta_desc_match:
                meta_desc_match = re.search(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']', html_content, re.IGNORECASE)
            meta_desc = meta_desc_match.group(1) if meta_desc_match else None
            desc_check = {
                'name': 'Meta Description',
                'status': 'pass' if meta_desc else 'fail',
                'score': 10 if meta_desc else 0,
                'max_score': 10,
                'message': 'Meta description present' if meta_desc else 'Missing meta description',
                'importance': 'high'
            }
            checks.append(desc_check)
            health_score += desc_check['score']

            # 5. Schema.org Structured Data (15 points)
            schema_scripts = re.findall(r'<script\s+type=["\']application/ld\+json["\'][^>]*>.*?</script>', html_content, re.IGNORECASE | re.DOTALL)
            schema_check = {
                'name': 'Structured Data (Schema.org)',
                'status': 'pass' if len(schema_scripts) > 0 else 'fail',
                'score': 15 if len(schema_scripts) > 0 else 0,
                'max_score': 15,
                'message': f'Found {len(schema_scripts)} structured data blocks' if schema_scripts else 'No structured data found',
                'importance': 'high'
            }
            checks.append(schema_check)
            health_score += schema_check['score']

            # 6. Heading Structure (10 points)
            h1_tags = re.findall(r'<h1[^>]*>.*?</h1>', html_content, re.IGNORECASE | re.DOTALL)
            headings_check = {
                'name': 'Proper Heading Structure',
                'status': 'pass' if len(h1_tags) == 1 else ('warning' if len(h1_tags) > 1 else 'fail'),
                'score': 10 if len(h1_tags) == 1 else (5 if len(h1_tags) > 1 else 0),
                'max_score': 10,
                'message': f'Found {len(h1_tags)} H1 tag(s)' + (' (Perfect)' if len(h1_tags) == 1 else ' (Should have exactly one)'),
                'importance': 'medium'
            }
            checks.append(headings_check)
            health_score += headings_check['score']

            # 7. Images with Alt Text (10 points)
            images = re.findall(r'<img[^>]*>', html_content, re.IGNORECASE)
            images_with_alt = [img for img in images if re.search(r'alt=["\'][^"\']*["\']', img)]
            alt_ratio = len(images_with_alt) / len(images) if images else 0
            alt_score = int(10 * alt_ratio)
            alt_check = {
                'name': 'Images with Alt Text',
                'status': 'pass' if alt_ratio >= 0.8 else ('warning' if alt_ratio >= 0.5 else 'fail'),
                'score': alt_score,
                'max_score': 10,
                'message': f'{len(images_with_alt)}/{len(images)} images have alt text ({int(alt_ratio*100)}%)' if images else 'No images found',
                'importance': 'medium'
            }
            checks.append(alt_check)
            health_score += alt_score

            # 8. Mobile-Friendly Viewport (5 points)
            viewport = re.search(r'<meta\s+name=["\']viewport["\']', html_content, re.IGNORECASE)
            mobile_check = {
                'name': 'Mobile-Friendly (Viewport)',
                'status': 'pass' if viewport else 'fail',
                'score': 5 if viewport else 0,
                'max_score': 5,
                'message': 'Viewport meta tag present' if viewport else 'Missing viewport meta tag',
                'importance': 'high'
            }
            checks.append(mobile_check)
            health_score += mobile_check['score']

        except requests.RequestException as e:
            logger.error(f"Error fetching domain {url}: {str(e)}")
            checks.append({
                'name': 'Website Accessibility',
                'status': 'fail',
                'score': 0,
                'max_score': 75,
                'message': f'Unable to access website: {str(e)}',
                'importance': 'critical'
            })

        # 9. robots.txt Check (2 points)
        try:
            robots_url = urljoin(url, '/robots.txt')
            robots_response = requests.get(robots_url, timeout=5)
            robots_exists = robots_response.status_code == 200
            robots_check = {
                'name': 'robots.txt',
                'status': 'pass' if robots_exists else 'warning',
                'score': 2 if robots_exists else 0,
                'max_score': 2,
                'message': 'robots.txt found' if robots_exists else 'robots.txt not found (optional but recommended)',
                'importance': 'low'
            }
            checks.append(robots_check)
            health_score += robots_check['score']
        except:
            checks.append({
                'name': 'robots.txt',
                'status': 'warning',
                'score': 0,
                'max_score': 2,
                'message': 'Unable to check robots.txt',
                'importance': 'low'
            })

        # 10. llms.txt Check (5 points) - AI/LLM crawler instructions
        try:
            llms_url = urljoin(url, '/llms.txt')
            llms_response = requests.get(llms_url, timeout=5)
            llms_exists = llms_response.status_code == 200
            llms_check = {
                'name': 'llms.txt',
                'status': 'pass' if llms_exists else 'warning',
                'score': 5 if llms_exists else 0,
                'max_score': 5,
                'message': 'llms.txt found - provides AI crawler guidance' if llms_exists else 'llms.txt not found (recommended for AI optimization)',
                'importance': 'medium'
            }
            checks.append(llms_check)
            health_score += llms_check['score']
        except:
            checks.append({
                'name': 'llms.txt',
                'status': 'warning',
                'score': 0,
                'max_score': 5,
                'message': 'Unable to check llms.txt',
                'importance': 'medium'
            })

        # 11. sitemap.xml Check (8 points)
        try:
            sitemap_url = urljoin(url, '/sitemap.xml')
            sitemap_response = requests.get(sitemap_url, timeout=5)
            sitemap_exists = sitemap_response.status_code == 200
            sitemap_check = {
                'name': 'XML Sitemap',
                'status': 'pass' if sitemap_exists else 'fail',
                'score': 8 if sitemap_exists else 0,
                'max_score': 8,
                'message': 'sitemap.xml found' if sitemap_exists else 'sitemap.xml not found',
                'importance': 'high'
            }
            checks.append(sitemap_check)
            health_score += sitemap_check['score']
        except:
            checks.append({
                'name': 'XML Sitemap',
                'status': 'fail',
                'score': 0,
                'max_score': 8,
                'message': 'Unable to check sitemap.xml',
                'importance': 'high'
            })

        # Calculate percentage
        health_percentage = int((health_score / max_score) * 100)

        # Determine health grade
        if health_percentage >= 80:
            grade = 'Excellent'
            grade_color = 'green'
        elif health_percentage >= 60:
            grade = 'Good'
            grade_color = 'blue'
        elif health_percentage >= 40:
            grade = 'Fair'
            grade_color = 'yellow'
        else:
            grade = 'Poor'
            grade_color = 'red'

        # Calculate summary
        summary = {
            'total_checks': len(checks),
            'passed': len([c for c in checks if c['status'] == 'pass']),
            'warnings': len([c for c in checks if c['status'] == 'warning']),
            'failed': len([c for c in checks if c['status'] == 'fail'])
        }

        # Save health check results to database
        from .models import DomainHealthCheck
        health_check = DomainHealthCheck.objects.create(
            domain=domain,
            health_score=health_score,
            max_score=max_score,
            percentage=health_percentage,
            grade=grade,
            grade_color=grade_color,
            checks=checks,
            total_checks=summary['total_checks'],
            passed_checks=summary['passed'],
            warning_checks=summary['warnings'],
            failed_checks=summary['failed'],
            checked_by=request.user
        )

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
            'checks': checks,
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
                model = genai.GenerativeModel('gemini-2.0-flash-exp')

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
            model = genai.GenerativeModel('gemini-2.0-flash-exp')

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