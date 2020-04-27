from collections import OrderedDict

from django.conf import settings
from rest_framework.pagination import BasePagination, PageNumberPagination
from rest_framework.response import Response

from .utils import BadRequestError


class WagtailPagination(BasePagination):
    def paginate_queryset(self, queryset, request, view=None):
        limit_max = getattr(settings, 'WAGTAILAPI_LIMIT_MAX', 20)

        try:
            offset = int(request.GET.get('offset', 0))
            if offset < 0:
                raise ValueError()
        except ValueError:
            raise BadRequestError("offset must be a positive integer")

        try:
            limit_default = 20 if not limit_max else min(20, limit_max)
            limit = int(request.GET.get('limit', limit_default))
            if limit < 0:
                raise ValueError()
        except ValueError:
            raise BadRequestError("limit must be a positive integer")

        if limit_max and limit > limit_max:
            raise BadRequestError(
                "limit cannot be higher than %d" % limit_max)

        start = offset
        stop = offset + limit

        self.view = view
        self.total_count = queryset.count()
        return queryset[start:stop]

    def get_paginated_response(self, data):
        data = OrderedDict([
            ('meta', OrderedDict([
                ('total_count', self.total_count),
            ])),
            ('items', data),
        ])
        return Response(data)


class ModelPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        next_page = None
        prev_page = None
        if self.get_next_link():
            next_page = self.page.number + 1
        if self.get_previous_link():
            prev_page = self.page.number - 1 if self.page.number >= 1 else 1

        data = {
            "meta": {
                "total_count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "next_page": next_page,
                "prev_page": prev_page,
            },
            "items": data
        }
        return Response(data)
