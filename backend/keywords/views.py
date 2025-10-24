from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Keyword
from .serializers import KeywordSerializer


@api_view(['GET', 'POST'])
def keyword_list(request):
    """List all keywords or create a new one"""
    if request.method == 'GET':
        keywords = Keyword.objects.all()
        serializer = KeywordSerializer(keywords, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = KeywordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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