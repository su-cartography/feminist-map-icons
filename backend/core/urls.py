from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .views import (
    IconViewSet,
    health,
    logout,
    me,
    register,
    request_contributor_access,
)

router = DefaultRouter()
router.register("icons", IconViewSet, basename="icon")

urlpatterns = [
    path("health/", health),
    path("auth/login/", obtain_auth_token),  # POST username + password ... token
    path("auth/logout/", logout),  # POST with the token ... token deleted
    path("auth/register/", register),  # POST create account (no contributor role)
    path("auth/me/", me),  # GET who is signed in + access-request status
    path("auth/request-contributor/", request_contributor_access),
    path("", include(router.urls)),
]