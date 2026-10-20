from rest_framework.routers import SimpleRouter

from .views import SampleViewSet

router = SimpleRouter(trailing_slash=False)
router.register("samples", SampleViewSet, basename="sample")

urlpatterns = router.urls