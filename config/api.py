"""
Shared API helpers.

RoadstarAPIView subclasses GenericAPIView so drf-spectacular can read
`serializer_class` from our hand-written get/post views.
"""

from rest_framework import serializers
from rest_framework.generics import GenericAPIView


class EmptySerializer(serializers.Serializer):
    """Placeholder when a view has no request/response body to document."""


class RoadstarAPIView(GenericAPIView):
    """
    Base for domain endpoints.

    We still implement get/post/patch ourselves (thin views → services).
    GenericAPIView is only here so OpenAPI/Swagger can discover serializers.
    """

    serializer_class = EmptySerializer

    def get_queryset(self):
        # Unused — list/detail data comes from selectors, not DRF generics.
        return []
