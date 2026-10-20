from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Result, ResultStatus, Sample, SampleStatus
from .serializers import ResultSerializer, SampleSerializer, SampleStatusSerializer
from .services import approve_result, change_sample_status, create_result


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

    @extend_schema(responses=ResultSerializer(many=True), tags=["results"])
    @action(detail=True, methods=["get"], url_path="results")
    def results(self, request, sample_id=None):
        sample = self.get_object()
        queryset = sample.results.select_related("sample")
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(ResultSerializer(page, many=True).data)


@extend_schema(tags=["results"])
class ResultViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Result.objects.select_related("sample")
    serializer_class = ResultSerializer
    lookup_url_kwarg = "result_id"

    @extend_schema(
        parameters=[
            OpenApiParameter("sample_id", str, required=False),
            OpenApiParameter("status", enum=ResultStatus.values, required=False),
            OpenApiParameter("parameter", str, required=False),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            params = self.request.query_params
            if params.get("sample_id"):
                queryset = queryset.filter(sample__sample_id=params["sample_id"])
            if params.get("status"):
                queryset = queryset.filter(status=params["status"])
            if params.get("parameter"):
                queryset = queryset.filter(parameter=params["parameter"])
        return queryset

    def perform_create(self, serializer):
        serializer.instance = create_result(**serializer.validated_data)

    @extend_schema(request=None, responses=ResultSerializer)
    @action(detail=True, methods=["patch"], url_path="approve")
    def approve(self, request, result_id=None):
        result = approve_result(self.get_object())
        return Response(self.get_serializer(result).data)
