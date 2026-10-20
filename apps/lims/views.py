from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Sample, SampleStatus
from .serializers import SampleSerializer, SampleStatusSerializer
from .services import change_sample_status


@extend_schema(tags=["samples"])
class SampleViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Sample.objects.all()
    serializer_class = SampleSerializer
    lookup_field = "sample_id"

    @extend_schema(
        parameters=[
            OpenApiParameter("status", enum=SampleStatus.values, required=False),
            OpenApiParameter("order_id", str, required=False),
            OpenApiParameter("client_id", str, required=False),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            for field in ("status", "order_id", "client_id"):
                value = self.request.query_params.get(field)
                if value:
                    queryset = queryset.filter(**{field: value})
        return queryset

    @extend_schema(request=SampleStatusSerializer, responses=SampleSerializer)
    @action(detail=True, methods=["patch"], url_path="status")
    def change_status(self, request, sample_id=None):
        sample = self.get_object()
        serializer = SampleStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sample = change_sample_status(sample, serializer.validated_data["status"])
        return Response(SampleSerializer(sample).data)
