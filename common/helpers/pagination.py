# pagination.py

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
import math

class CustomPagination(PageNumberPagination):
    page_size = 10  # Default page size
    page_size_query_param = 'page_size'  # Allow client to set custom page size
    max_page_size = 100  # Maximum page size allowed
    page_query_param = 'page'  # Query parameter for page number

    def get_paginated_response(self, data):
        """
        Override the default get_paginated_response to include additional metadata:
        - total_pages
        - current_page
        - next and previous links
        - has_next and has_previous flags
        """
        total_pages = math.ceil(self.page.paginator.count / self.page_size)  # Calculate total pages

        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            },
            'meta': {
                'total_records': self.page.paginator.count,  # Total number of records
                'total_pages': total_pages,  # Total pages calculated based on records and page size
                'current_page': self.page.number,  # Current page number
                'page_size': self.page_size,  # Page size
                'has_next': self.page.has_next(),  # Is there a next page?
                'has_previous': self.page.has_previous(),  # Is there a previous page?
            },
            'results': data  # The actual paginated data
        })
