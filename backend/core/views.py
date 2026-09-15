from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Icon
from .serializers import IconSerializer


# Simple check: "Is the API running?"
@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


# Handles list, detail, create, update, and delete for icons.
class IconViewSet(viewsets.ModelViewSet):
    serializer_class = IconSerializer
    # Use unique_id in the URL instead of the numeric database id
    # e.g. /api/icons/00e8059e/
    lookup_field = "unique_id"
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    # Decide which icons to return for this request
    def get_queryset(self):
        # Load icons and their secondary tags in an efficient way
        qs = Icon.objects.prefetch_related("tags").all()

        # Public list/detail: only show published icons 
        if self.action in ("list", "retrieve"):
            qs = qs.filter(status=Icon.Status.PUBLISHED)

        # Optional search: /api/icons/?q=park
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(unique_id__icontains=q)
                | Q(primary_tag__icontains=q)
                | Q(designer__icontains=q)
                | Q(uploader__icontains=q)
                | Q(icon_description__icontains=q)
                | Q(icon_geography__icontains=q)
                | Q(tags__name__icontains=q)
            ).distinct()  # distinct() avoids duplicate rows when matching tags

        return qs
