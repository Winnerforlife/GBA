from rest_framework.routers import SimpleRouter

from .views import ResultViewSet, SampleViewSet

router = SimpleRouter(trailing_slash=False)
router.register("samples", SampleViewSet, basename="sample")
router.register("results", ResultViewSet, basename="result")

urlpatterns = router.urls