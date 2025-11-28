from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db import IntegrityError
from django.utils import timezone
from .models import Keyword, SecondaryKeyword
from .serializers import KeywordSerializer, SecondaryKeywordSerializer
from domains.models import Domain
from domains.services import schedule_domain_processing


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def keyword_list(request):
    """List all keywords or create a new one"""
    if request.method == 'GET':
        # Filter keywords by user's organization
        if request.user.role == 'super_admin':
            keywords = Keyword.objects.filter(domain__organisation=request.user.organisation)
        else:
            # Users can only see keywords for domains they have access to
            from domains.models import DomainAccess
            domain_ids = DomainAccess.objects.filter(
                user=request.user,
                domain__organisation=request.user.organisation
            ).values_list('domain_id', flat=True)
            keywords = Keyword.objects.filter(domain_id__in=domain_ids)
        
        serializer = KeywordSerializer(keywords, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Only admins can create keywords
        if request.user.role not in ['admin', 'super_admin']:
            return Response(
                {'error': 'Only organization administrators can add keywords'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = KeywordSerializer(data=request.data)
        if serializer.is_valid():
            # Normalize keyword to lowercase
            keyword_text = serializer.validated_data.get('keyword', '').strip().lower()
            if not keyword_text or len(keyword_text) > 255:
                return Response(
                    {'error': 'Keyword must be non-empty and less than 255 characters'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            domain = serializer.validated_data['domain']
            
            # Verify domain belongs to user's organization
            if domain.organisation != request.user.organisation:
                return Response(
                    {'error': 'Domain does not belong to your organization'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            try:
                with transaction.atomic():
                    # Create keyword with normalized text
                    keyword, created = Keyword.objects.get_or_create(
                        keyword=keyword_text,
                        domain=domain,
                        defaults={
                            'auto_generate_prompts': True,
                            'priority': 0
                        }
                    )
                    
                    if not created:
                        return Response(
                            {'error': 'Keyword already exists for this domain'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Check if domain should be reinitialized for processing
                    current_status = domain.processing_status
                    reinit_triggered = False
                    
                    if current_status in ['COMP', 'FAIL', 'INIT']:
                        # Domain is not processing - can safely reinit
                        domain.processing_status = 'INIT'
                        domain.track_message = 'Ready for processing with new keywords'
                        domain.tracked_at = timezone.now()
                        domain.save(update_fields=['processing_status', 'track_message', 'tracked_at', 'modified_at'])
                        
                        # Schedule processing
                        reinit_triggered = schedule_domain_processing(domain)
                    elif current_status == 'PROC':
                        # Domain is processing - don't interrupt, just mark keywords as available
                        domain.track_message = f'Processing in progress. New keyword "{keyword_text}" queued for next cycle'
                        domain.save(update_fields=['track_message', 'modified_at'])
                    
                    return Response({
                        'message': 'Keyword created successfully',
                        'keyword': KeywordSerializer(keyword).data,
                        'reinit_triggered': reinit_triggered,
                        'current_status': domain.processing_status,
                        'note': 'Keywords will be processed automatically when current cycle completes' if current_status == 'PROC' else None
                    }, status=status.HTTP_201_CREATED)
                    
            except IntegrityError:
                return Response(
                    {'error': 'Keyword already exists for this domain'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                return Response(
                    {'error': f'Failed to create keyword: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_create_keywords(request):
    """Bulk create keywords with semantic metadata"""
    # Only admins can create keywords
    if request.user.role not in ['admin', 'super_admin']:
        return Response(
            {'error': 'Only organization administrators can add keywords'},
            status=status.HTTP_403_FORBIDDEN
        )

    domain_id = request.data.get('domain_id')
    keywords_data = request.data.get('keywords', [])

    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    if not keywords_data or not isinstance(keywords_data, list):
        return Response({'error': 'keywords must be a non-empty list'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        domain = Domain.objects.get(pk=domain_id, organisation=request.user.organisation)
    except Domain.DoesNotExist:
        return Response({'error': 'Domain not found or not in your organization'}, status=status.HTTP_404_NOT_FOUND)

    created_keywords = []
    skipped_keywords = []

    with transaction.atomic():
        for kw_data in keywords_data:
            keyword_text = kw_data.get('keyword', '').strip().lower()

            if not keyword_text or len(keyword_text) > 255:
                skipped_keywords.append({'keyword': keyword_text, 'reason': 'Invalid keyword length'})
                continue

            # Try to create keyword with semantic metadata
            keyword, created = Keyword.objects.get_or_create(
                keyword=keyword_text,
                domain=domain,
                defaults={
                    'volume_level': kw_data.get('volume_level'),
                    'intent': kw_data.get('intent'),
                    'entity': kw_data.get('entity'),
                    'attribute': kw_data.get('attribute'),
                    'variable': kw_data.get('variable'),
                    'source': kw_data.get('source', 'ai-generated'),
                    'topic': kw_data.get('topic'),
                    'cluster_id': kw_data.get('cluster_id'),
                }
            )

            if created:
                created_keywords.append(KeywordSerializer(keyword).data)
            else:
                skipped_keywords.append({'keyword': keyword_text, 'reason': 'Already exists'})

        # Update domain processing status if keywords were created
        if created_keywords:
            current_status = domain.processing_status
            reinit_triggered = False

            if current_status in ['COMP', 'FAIL', 'INIT']:
                domain.processing_status = 'INIT'
                domain.track_message = f'Ready for processing with {len(created_keywords)} new keywords'
                domain.tracked_at = timezone.now()
                domain.save(update_fields=['processing_status', 'track_message', 'tracked_at', 'modified_at'])
                reinit_triggered = schedule_domain_processing(domain)

    return Response({
        'success': True,
        'created_count': len(created_keywords),
        'skipped_count': len(skipped_keywords),
        'created_keywords': created_keywords[:10],  # Return first 10 for confirmation
        'skipped_keywords': skipped_keywords,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_create_secondary_keywords(request):
    """Bulk create secondary keywords (unselected AI-generated keywords)"""
    # Only admins can create keywords
    if request.user.role not in ['admin', 'super_admin']:
        return Response(
            {'error': 'Only organization administrators can add keywords'},
            status=status.HTTP_403_FORBIDDEN
        )

    domain_id = request.data.get('domain_id')
    keywords_data = request.data.get('keywords', [])

    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    if not keywords_data or not isinstance(keywords_data, list):
        return Response({'error': 'keywords must be a non-empty list'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        domain = Domain.objects.get(pk=domain_id, organisation=request.user.organisation)
    except Domain.DoesNotExist:
        return Response({'error': 'Domain not found or not in your organization'}, status=status.HTTP_404_NOT_FOUND)

    created_keywords = []
    skipped_keywords = []

    with transaction.atomic():
        for kw_data in keywords_data:
            keyword_text = kw_data.get('keyword', '').strip().lower()

            if not keyword_text or len(keyword_text) > 255:
                skipped_keywords.append({'keyword': keyword_text, 'reason': 'Invalid keyword length'})
                continue

            # Try to create secondary keyword with semantic metadata
            keyword, created = SecondaryKeyword.objects.get_or_create(
                keyword=keyword_text,
                domain=domain,
                defaults={
                    'volume_level': kw_data.get('volume_level'),
                    'intent': kw_data.get('intent'),
                    'entity': kw_data.get('entity'),
                    'attribute': kw_data.get('attribute'),
                    'variable': kw_data.get('variable'),
                    'source': kw_data.get('source', 'ai-generated'),
                    'topic': kw_data.get('topic'),
                    'cluster_id': kw_data.get('cluster_id'),
                }
            )

            if created:
                created_keywords.append(SecondaryKeywordSerializer(keyword).data)
            else:
                skipped_keywords.append({'keyword': keyword_text, 'reason': 'Already exists'})

    return Response({
        'success': True,
        'created_count': len(created_keywords),
        'skipped_count': len(skipped_keywords),
        'created_keywords': created_keywords[:10],  # Return first 10 for confirmation
        'skipped_keywords': skipped_keywords,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
def keyword_detail(request, pk):
    """Retrieve, update or delete a keyword"""
    keyword = get_object_or_404(Keyword, pk=pk)

    if request.method == 'GET':
        serializer = KeywordSerializer(keyword)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = KeywordSerializer(keyword, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        keyword.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)