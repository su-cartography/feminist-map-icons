"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.urls import include

# MEDIA_ROOT is  not served here. static() publishes every file under it at a
# guessable /media/ path with no check of the icon's status or its owner, so the artwork of
# an icon still in review was readable by anyone (issue #18). Icon files are served by
# /api/icons/<unique_id>/png/ and /svg/ instead, which run the same visibility rules as the
# rest of the API. Nothing else lives under media/, so nothing else lost a URL.
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
]