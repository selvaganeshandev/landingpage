from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Domain
from .serializers import DomainSerializer, DomainDetailSerializer


@api_view(['GET', 'POST'])
def domain_list(request):
    """List all domains or create a new one"""
    if request.method == 'GET':
        domains = Domain.objects.all()
        serializer = DomainSerializer(domains, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = DomainSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def domain_detail(request, pk):
    """Retrieve, update or delete a domain"""
    domain = get_object_or_404(Domain, pk=pk)
    
    if request.method == 'GET':
        serializer = DomainDetailSerializer(domain)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = DomainSerializer(domain, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        domain.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def domain_keywords(request, pk):
    """Get all keywords for a domain"""
    domain = get_object_or_404(Domain, pk=pk)
    keywords = domain.keywords.all()
    from keywords.serializers import KeywordSerializer
    serializer = KeywordSerializer(keywords, many=True)
    return Response(serializer.data)