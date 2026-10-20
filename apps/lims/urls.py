from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import ResultViewSet, SampleExportView, SampleViewSet

router = SimpleRouter(trailing_slash=False)
router.register("samples", SampleViewSet, basename="sample")
router.register("results", ResultViewSet, basename="result")

urlpatterns = [
    *router.urls,
    path(
        "integration/export/<str:sample_id>",
        SampleExportView.as_view(),
        name="sample-export",
    ),
]
