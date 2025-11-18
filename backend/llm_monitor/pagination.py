"""
Custom pagination classes for the LLM Monitor API.
"""
from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    """
    Custom pagination class that allows clients to specify page size via query parameter.

    Usage in URL:
        ?page=1&page_size=100

    Defaults:
        - page_size: 20 (if not specified)
        - max_page_size: 1000 (hard limit)
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000
