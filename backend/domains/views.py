from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction
from django.db import IntegrityError
from django.conf import settings
from .models import Domain, DomainAccess
from .serializers import (
    DomainSerializer, DomainDetailSerializer,
    DomainAccessSerializer, DomainAccessCreateSerializer
)
from authentication.serializers import AccountSerializer
from authentication.models import Account
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

        # Normalize domain name (strip scheme, www, path, port)
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
            data['name'] = normalized
        
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
            # Use transaction to ensure domain and keywords are created atomically
            try:
                with transaction.atomic():
                    domain = serializer.save()
                    
                    # Create keywords in the same transaction
                    from keywords.models import Keyword
                    created_keywords = []
                    for keyword_text in keywords_list:
                        try:
                            keyword, created = Keyword.objects.get_or_create(
                                keyword=keyword_text,
                                domain=domain,
                                defaults={
                                    'auto_generate_prompts': True,
                                    'priority': 0
                                }
                            )
                            if created:
                                created_keywords.append(keyword_text)
                        except IntegrityError:
                            # Handle race condition - keyword already exists
                            pass
                    
                    # Verify at least one keyword was created
                    if not Keyword.objects.filter(domain=domain).exists():
                        return Response(
                            {'error': 'Failed to create keywords. Please try again.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                    
                    return Response({
                        'message': 'Domain added successfully',
                        'domain': DomainSerializer(domain).data,
                        'keywords_created': len(created_keywords)
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
        
        domain.delete()
        return Response({
            'message': 'Domain deleted successfully'
        })


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