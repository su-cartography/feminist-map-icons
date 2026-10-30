from pathlib import Path

from django.db.models import Q
from django.http import FileResponse
from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from .models import Icon
from .permissions import IsContributorOrReadOnly, IsOwnerOrModerator, IsReviewer
from .roles import is_admin, is_moderator
from .serializers import IconSerializer, IconStatusSerializer


# Simple check: "Is the API running?"
# Says AllowAny out loud because the project default now demands a login: a liveness probe
# that needs credentials is no use to a monitor or a load balancer.
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})


# The icon file endpoints answer with bytes, not JSON. DRF picks a renderer before the
# handler runs, and JSON is the only one configured project-wide so, a client asking
# precisely for "Accept: image/png" would be told 406 before it reached the file.
class IconFileRenderer(BaseRenderer):
    media_type = "*/*"
    format = "file"
    charset = None

    def render(self, data, *args, **kwargs):
        return data


# Handles list, detail, create, update, and delete for icons.
class IconViewSet(viewsets.ModelViewSet):
    serializer_class = IconSerializer
    # First class gates the request ("may you write at all"), second gates the row
    # ("is it yours, and still unapproved"). Both have to pass.
    permission_classes = [IsContributorOrReadOnly, IsOwnerOrModerator]
    # Use unique_id in the URL instead of the numeric database id
    # e.g. /api/icons/00e8059e/
    lookup_field = "unique_id"
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    # Statuses an author can resubmit from, putting the icon back in the review queue.
    SUBMITTABLE_FROM = (
        Icon.Status.DRAFT,
        Icon.Status.CHANGES_REQUESTED,
        Icon.Status.REJECTED,
    )

    # What a moderator can set through review/. Anything else (publishing, or sending an
    # icon back to draft) is the library admin's call: approve is not publish.
    REVIEW_OUTCOMES = (
        Icon.Status.APPROVED,
        Icon.Status.REJECTED,
        Icon.Status.CHANGES_REQUESTED,
    )

    # Decide which icons this request can see. Applies to every action, not just
    # list/retrieve, so a write can never reach a row the caller cannot see.
    def get_queryset(self):
        # Load icons and their secondary tags in an efficient way
        # order_by keeps page boundaries stable; DRF warns if the list queryset is unordered.
        qs = Icon.objects.prefetch_related("tags").order_by("unique_id")

        user = self.request.user
        if not is_moderator(user):
            # Visitors see published only; contributors also see their own submissions,
            # so a fresh upload is visible to its author instead of 404ing.
            visible = Q(status=Icon.Status.PUBLISHED)
            if user.is_authenticated:
                visible |= Q(created_by=user)
            qs = qs.filter(visible)

        # Optional search: /api/icons/?q=park
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(primary_tag__icontains=q)
                | Q(tags__name__icontains=q)
                | Q(icon_description__icontains=q)
                | Q(designer__icontains=q)
                | Q(uploader__icontains=q)
                | Q(icon_geography__icontains=q)
                | Q(where_created__icontains=q)
                | Q(unique_id__icontains=q)
            ).distinct()  # distinct() avoids duplicate rows when matching tags

        return qs

    # Record who uploaded it, so ownership can be checked later.
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    # POST /api/icons/<unique_id>/submit/
    # The author (or a moderator) puts a draft back in the review queue.
    @action(detail=True, methods=["post"])
    def submit(self, request, unique_id=None):
        icon = self.get_object()  # runs IsOwnerOrModerator on the row
        if icon.status not in self.SUBMITTABLE_FROM:
            return Response(
                {"detail": f"Cannot submit an icon that is {icon.status}."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        icon.status = Icon.Status.PENDING
        icon.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(icon).data)

    # POST /api/icons/<unique_id>/review/ {"status": "approved"}
    # Status changes live here, not in the serializer, so a permission class guards them
    # instead of a check that one code path could miss.
    @action(detail=True, methods=["post"], permission_classes=[IsReviewer])
    def review(self, request, unique_id=None):
        icon = self.get_object()
        serializer = IconStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        if new_status not in self.REVIEW_OUTCOMES and not is_admin(request.user):
            raise PermissionDenied(
                f"Only a library admin can set an icon to {new_status}."
            )

        # Taking an icon back out of published is unpublishing, which is the publish right
        # in reverse, so it is the admin's call too. Without this a moderator could move a
        # published icon to changes_requested -- a status LOCKED_TO_MODERATORS does not
        # cover -- and hand its author edit rights on already-published content.
        if icon.status == Icon.Status.PUBLISHED and not is_admin(request.user):
            raise PermissionDenied(
                "Only a library admin can change the status of a published icon."
            )

        icon.status = new_status
        icon.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(icon).data)

    # GET /api/icons/<unique_id>/png/   and   GET /api/icons/<unique_id>/svg/
    # The files are served through the API rather than straight off /media/, because a raw
    # file path ha no status and no owner; anyone who knew or guessed the path could read
    # artwork that is still in review. These go through get_object(), so a file is
    # as visible as the row it belongs to -- published to everyone, unpublished to its
    # owner and to moderators, invisible (404, not 403) to anyone else.
    @action(detail=True, methods=["get"], renderer_classes=[IconFileRenderer])
    def png(self, request, unique_id=None):
        return self._serve_file(self.get_object(), "png_file", "image/png")

    @action(detail=True, methods=["get"], renderer_classes=[IconFileRenderer])
    def svg(self, request, unique_id=None):
        return self._serve_file(self.get_object(), "svg_file", "image/svg+xml")

    # An SVG is markup, not a bitmap: it can carry a <script>, and served inline from this
    # origin that script would run with the API's own session cookie. Sending it as a
    # download stops a direct visit from rendering it, while the gallery is unaffected --
    # Content-Disposition is ignored for an <img src>, and an SVG in an <img> runs no
    # script.
    SERVE_AS_DOWNLOAD = ("image/svg+xml",)

    def _serve_file(self, icon, field_name, content_type):
        stored = getattr(icon, field_name)
        if not stored:
            raise NotFound(f"This icon has no {field_name.split('_')[0].upper()} file.")

        try:
            handle = stored.open("rb")
        except FileNotFoundError:
            # The row says there is a file and storage disagrees -- a 500 here would read
            # as an outage rather than as the one missing file it is.
            raise NotFound("The file for this icon is missing from storage.")

        response = FileResponse(
            handle,
            content_type=content_type,
            filename=Path(stored.name).name,
            as_attachment=content_type in self.SERVE_AS_DOWNLOAD,
        )
        # Say what the bytes are and have the browser believe it, rather than sniffing a
        # different type out of the content.
        response["X-Content-Type-Options"] = "nosniff"
        if icon.status != Icon.Status.PUBLISHED:
            # Whether this file is readable depends on who asked, so it can't be held
            # in any shared cache and handed to the next person.
            response["Cache-Control"] = "private, no-store"
        return response
