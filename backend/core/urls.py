from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import IconViewSet, health

router = DefaultRouter()
router.register("icons", IconViewSet, basename="icon")

urlpatterns = [
    path("health/", health),
    path("", include(router.urls)),
]