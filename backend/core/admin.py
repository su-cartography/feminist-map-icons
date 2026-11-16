from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group, User

from .models import ContributorAccessRequest, Icon, Tag
from .roles import CONTRIBUTOR, is_admin


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Icon)
class IconAdmin(admin.ModelAdmin):
    list_display = ("unique_id", "primary_tag", "designer", "status", "created_by", "updated_at")
    list_filter = ("status",)
    search_fields = ("unique_id", "primary_tag", "designer", "uploader", "icon_description")
    filter_horizontal = ("tags",)

    # The admin is a second way in, and it does not go through the API's permission
    # classes. Moderators are given is_staff to review here, and the role groups give them
    # change_icon, so without this the status dropdown let them publish directly and
    # "approve is not publish" held only on the API. created_by is locked for the same
    # reason: the form would otherwise let them reassign authorship.
    RESERVED_TO_ADMINS = ("status", "created_by")

    def get_readonly_fields(self, request, obj=None):
        if is_admin(request.user):
            return super().get_readonly_fields(request, obj)
        return tuple(super().get_readonly_fields(request, obj)) + self.RESERVED_TO_ADMINS

    # A readonly field is simply absent from the add form, so a non-admin creating an icon
    # here would silently get the model default (pending). That is the right state, but be
    # explicit rather than relying on it.
    def save_model(self, request, obj, form, change):
        if not change and not is_admin(request.user):
            obj.status = Icon.Status.PENDING
        super().save_model(request, obj, form, change)


@admin.register(ContributorAccessRequest)
class ContributorAccessRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "note", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("user__username", "user__email", "note")
    readonly_fields = ("user", "note", "created_at", "updated_at")
    ordering = ("-created_at",)

    def has_module_permission(self, request):
        return is_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_admin(request.user)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return is_admin(request.user)


# Approving a contributor account through Django's user form means handing out
# auth.change_user, and that form also edits is_superuser, groups and user_permissions --
# one mis-click away from granting the publish right only Admins are meant to hold, or a
# superuser who bypasses every check in roles.py. These two actions can add or remove one
# group and nothing else, so the worst they can do is what they say on the tin.
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    actions = ("grant_contributor_access", "revoke_contributor_access")

    # Gated on our own role check rather than Django's "change" permission, which is the
    # auth.change_user these actions exist to avoid needing. An action the check rejects
    # is dropped from get_actions(), and response_action() resolves a posted action name
    # against that same dict, so hand-posting the name gets nowhere either.
    def has_manage_contributors_permission(self, request):
        return is_admin(request.user)

    @admin.action(
        permissions=["manage_contributors"],
        description="Grant contributor access (may upload icons)",
    )
    def grant_contributor_access(self, request, queryset):
        self._set_contributor_access(request, queryset, grant=True)

    @admin.action(
        permissions=["manage_contributors"],
        description="Revoke contributor access",
    )
    def revoke_contributor_access(self, request, queryset):
        self._set_contributor_access(request, queryset, grant=False)

    def _set_contributor_access(self, request, queryset, grant):
        group = Group.objects.get(name=CONTRIBUTOR)
        # Narrow to the rows the action actually changes, so selecting ten users who are
        # already contributors reports nothing rather than claiming ten approvals.
        if grant:
            changed = list(queryset.exclude(groups=group))
            group.user_set.add(*changed)
            ContributorAccessRequest.objects.filter(
                user__in=changed,
                status=ContributorAccessRequest.Status.PENDING,
            ).update(status=ContributorAccessRequest.Status.GRANTED)
        else:
            changed = list(queryset.filter(groups=group))
            group.user_set.remove(*changed)
            ContributorAccessRequest.objects.filter(
                user__in=changed,
                status=ContributorAccessRequest.Status.GRANTED,
            ).update(status=ContributorAccessRequest.Status.CLOSED)

        if not changed:
            self.message_user(request, "No accounts needed that change.")
            return
        verb = "can now upload icons" if grant else "can no longer upload icons"
        names = ", ".join(sorted(user.get_username() for user in changed))
        self.message_user(request, f"{names} {verb}.")
