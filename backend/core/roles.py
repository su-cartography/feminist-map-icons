# The three roles from docs/permissions.md, as Django Groups.
# Role membership is a group, never is_staff: moderators need is_staff to reach the
# Django admin, so treating that flag as a role would also hand them publish rights.

CONTRIBUTOR = "Contributor"
MODERATOR = "Moderator"
ADMIN = "Admin"

# Django admin permissions per role, written as "app_label.codename", so the groups are
# useful in the admin too. Publishing is a status value, not a model permission, so
# "approve but don't publish" can only be expressed in the API.
#
# Only Admin gets the auth.User rights, which is how contributor accounts get approved
# until the real workflow lands. Moderators are left out on purpose even though the matrix
# gives them account approval: the admin's user form exposes is_superuser, groups and
# user_permissions, so auth.change_user lets the holder promote themselves and take the
# publish right this whole module exists to withhold. Approving an account without that
# escalation needs a narrow action of our own, not Django's edit-everything form.
ROLE_PERMISSIONS = {
    CONTRIBUTOR: (
        "core.add_icon", "core.change_icon", "core.view_icon",
        "core.add_tag", "core.view_tag",
    ),
    MODERATOR: (
        "core.add_icon", "core.change_icon", "core.delete_icon", "core.view_icon",
        "core.add_tag", "core.change_tag", "core.view_tag",
    ),
    ADMIN: (
        "core.add_icon", "core.change_icon", "core.delete_icon", "core.view_icon",
        "core.add_tag", "core.change_tag", "core.delete_tag", "core.view_tag",
        "core.view_contributoraccessrequest",
        "core.change_contributoraccessrequest",
        "auth.add_user", "auth.change_user", "auth.view_user",
    ),
}


def _role_names(user):
    if not (user and user.is_authenticated):
        return frozenset()
    return frozenset(user.groups.values_list("name", flat=True))


# The roles nest, so each check accepts the roles above it. A superuser counts as Admin.

# Library admin: publishes icons, full CRUD.
def is_admin(user):
    if not (user and user.is_authenticated):
        return False
    return user.is_superuser or ADMIN in _role_names(user)


# Moderator: reviews submissions and manages others' icons, but cannot publish.
def is_moderator(user):
    if not (user and user.is_authenticated):
        return False
    return user.is_superuser or bool({ADMIN, MODERATOR} & _role_names(user))


# Contributor: uploads icons and edits their own unapproved ones.
def is_contributor(user):
    if not (user and user.is_authenticated):
        return False
    return user.is_superuser or bool(
        {ADMIN, MODERATOR, CONTRIBUTOR} & _role_names(user)
    )


# Create the three groups and reset their permissions. Safe to run repeatedly.
def sync_roles():
    from django.contrib.auth.models import Group, Permission
    from django.db.models import Q

    for name, labels in ROLE_PERMISSIONS.items():
        wanted = Q()
        for label in labels:
            app_label, codename = label.split(".")
            wanted |= Q(content_type__app_label=app_label, codename=codename)

        group, _ = Group.objects.get_or_create(name=name)
        found = Permission.objects.filter(wanted)
        # A typo here would silently under-permission a role, so fail loudly instead.
        if found.count() != len(labels):
            missing = set(labels) - {
                f"{p.content_type.app_label}.{p.codename}" for p in found
            }
            raise LookupError(f"unknown permissions for {name}: {sorted(missing)}")
        group.permissions.set(found)
