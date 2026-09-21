from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .views import IconViewSet, health

router = DefaultRouter()
router.register("icons", IconViewSet, basename="icon")

urlpatterns = [
    path("health/", health),
    path("auth/login/", obtain_auth_token), # POST username + password ... token
    path("", include(router.urls)),
]