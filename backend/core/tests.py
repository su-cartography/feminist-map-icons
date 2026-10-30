import struct
import tempfile
import zlib
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse as django_reverse
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from .admin import UserAdmin
from .models import Icon, Tag
from .permissions import IsContributorOrReadOnly
from .roles import ADMIN, CONTRIBUTOR, MODERATOR, ROLE_PERMISSIONS
from .validators import MAX_ICON_FILE_SIZE

User = get_user_model()


def in_role(user, role):
    """Put a user in a role group. post_migrate already made the groups here."""
    user.groups.add(Group.objects.get(name=role))
    return user


def icon_url(unique_id, suffix=None):
    name = "icon-detail" if suffix is None else f"icon-{suffix}"
    return reverse(name, kwargs={"unique_id": unique_id})


def list_rows(response):
    """List payloads are paginated: {count, next, previous, results}."""
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


class IconPermissionTests(APITestCase):
    """The two holes found by hand on 2026-10-01: publish-bypass and delete-anything."""

    @classmethod
    def setUpTestData(cls):
        cls.author = in_role(User.objects.create_user("author", password="pw"), CONTRIBUTOR)
        cls.other = in_role(User.objects.create_user("other", password="pw"), CONTRIBUTOR)
        cls.moderator = in_role(
            User.objects.create_user("curator", password="pw", is_staff=True), MODERATOR
        )
        cls.admin = in_role(
            User.objects.create_user("librarian", password="pw", is_staff=True), ADMIN
        )

        # A published icon with no owner, standing in for the imported rows.
        cls.published = Icon.objects.create(
            unique_id="curated1",
            primary_tag="park",
            status=Icon.Status.PUBLISHED,
        )
        # One of the author's own, still in the queue.
        cls.pending = Icon.objects.create(
            unique_id="mine1",
            primary_tag="bench",
            status=Icon.Status.PENDING,
            created_by=cls.author,
        )

    # --- issue 1: status is not client-writable ------------------------------------

    def test_create_lands_in_pending_even_when_published_is_requested(self):
        self.client.force_authenticate(self.author)
        response = self.client.post(
            reverse("icon-list"),
            {"unique_id": "probe1", "status": "published"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Icon.Status.PENDING)
        self.assertEqual(Icon.objects.get(unique_id="probe1").status, Icon.Status.PENDING)

    def test_patch_cannot_publish_your_own_icon(self):
        self.client.force_authenticate(self.author)
        response = self.client.patch(
            icon_url("mine1"), {"status": "published"}, format="json"
        )
        # The write succeeds but status is read-only, so it is ignored and the icon
        # stays in the queue. This is the request that used to skip review.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Icon.Status.PENDING)

    def test_review_action_is_reviewers_only(self):
        self.client.force_authenticate(self.author)
        response = self.client.post(
            icon_url("mine1", "review"), {"status": "published"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Icon.Status.PENDING)

    def test_admin_can_publish_through_the_review_action(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            icon_url("mine1", "review"), {"status": "published"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Icon.Status.PUBLISHED)

    # A published icon is only the admin's to move. Otherwise a moderator could send it
    # to changes_requested -- which LOCKED_TO_MODERATORS does not cover -- and hand the
    # author edit rights on content that was already published.
    def test_a_moderator_cannot_re_review_a_published_icon(self):
        self.client.force_authenticate(self.moderator)
        response = self.client.post(
            icon_url("curated1", "review"),
            {"status": Icon.Status.CHANGES_REQUESTED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.published.refresh_from_db()
        self.assertEqual(self.published.status, Icon.Status.PUBLISHED)

    def test_a_library_admin_can_re_review_a_published_icon(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            icon_url("curated1", "review"),
            {"status": Icon.Status.CHANGES_REQUESTED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_review_rejects_a_status_outside_the_choices(self):
        self.client.force_authenticate(self.moderator)
        response = self.client.post(
            icon_url("mine1", "review"), {"status": "live"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_author_can_resubmit_after_changes_requested(self):
        self.pending.status = Icon.Status.CHANGES_REQUESTED
        self.pending.save(update_fields=["status"])
        self.client.force_authenticate(self.author)
        response = self.client.post(icon_url("mine1", "submit"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Icon.Status.PENDING)

    def test_submit_is_rejected_when_already_pending(self):
        self.client.force_authenticate(self.author)
        response = self.client.post(icon_url("mine1", "submit"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- issue 2: you cannot touch rows that are not yours -------------------------

    # Denied by ownership rather than by status: curated1 has no created_by at all.
    def test_a_contributor_cannot_delete_an_icon_that_is_not_theirs(self):
        self.client.force_authenticate(self.other)
        response = self.client.delete(icon_url("curated1"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Icon.objects.filter(unique_id="curated1").exists())

    def test_a_contributor_cannot_patch_an_icon_that_is_not_theirs(self):
        self.client.force_authenticate(self.other)
        response = self.client.patch(
            icon_url("curated1"), {"designer": "me, actually"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.published.refresh_from_db()
        self.assertEqual(self.published.designer, "")

    def test_author_cannot_edit_their_icon_once_published(self):
        self.pending.status = Icon.Status.PUBLISHED
        self.pending.save(update_fields=["status"])
        self.client.force_authenticate(self.author)
        response = self.client.patch(
            icon_url("mine1"), {"designer": "swapped"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_cannot_edit_their_icon_once_approved(self):
        self.pending.status = Icon.Status.APPROVED
        self.pending.save(update_fields=["status"])
        self.client.force_authenticate(self.author)
        response = self.client.patch(
            icon_url("mine1"), {"designer": "swapped after review"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.designer, "")

    def test_author_cannot_delete_their_icon_once_approved(self):
        self.pending.status = Icon.Status.APPROVED
        self.pending.save(update_fields=["status"])
        self.client.force_authenticate(self.author)
        response = self.client.delete(icon_url("mine1"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Icon.objects.filter(unique_id="mine1").exists())

    # The author keeps the changes-requested loop: still theirs to edit and resubmit.
    def test_author_can_still_edit_after_changes_are_requested(self):
        self.pending.status = Icon.Status.CHANGES_REQUESTED
        self.pending.save(update_fields=["status"])
        self.client.force_authenticate(self.author)
        response = self.client.patch(
            icon_url("mine1"), {"designer": "fixed it"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_moderator_can_still_edit_an_approved_icon(self):
        self.pending.status = Icon.Status.APPROVED
        self.pending.save(update_fields=["status"])
        self.client.force_authenticate(self.moderator)
        response = self.client.patch(
            icon_url("mine1"), {"designer": "tidied"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_another_users_pending_icon_is_invisible_not_merely_forbidden(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.get(icon_url("mine1")).status_code, status.HTTP_404_NOT_FOUND
        )
        self.assertEqual(
            self.client.delete(icon_url("mine1")).status_code, status.HTTP_404_NOT_FOUND
        )

    def test_author_can_edit_and_delete_their_own_unapproved_icon(self):
        self.client.force_authenticate(self.author)
        patch = self.client.patch(
            icon_url("mine1"), {"designer": "the author"}, format="json"
        )
        self.assertEqual(patch.status_code, status.HTTP_200_OK)
        delete = self.client.delete(icon_url("mine1"))
        self.assertEqual(delete.status_code, status.HTTP_204_NO_CONTENT)

    def test_moderator_can_edit_an_imported_icon_with_no_owner(self):
        self.client.force_authenticate(self.moderator)
        response = self.client.patch(
            icon_url("curated1"), {"designer": "curated"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_writes_are_rejected(self):
        self.assertEqual(
            self.client.post(reverse("icon-list"), {"unique_id": "anon"}, format="json").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.delete(icon_url("curated1")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class IconVisibilityTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = in_role(User.objects.create_user("author", password="pw"), CONTRIBUTOR)
        cls.moderator = in_role(
            User.objects.create_user("curator", password="pw", is_staff=True), MODERATOR
        )
        cls.admin = in_role(
            User.objects.create_user("librarian", password="pw", is_staff=True), ADMIN
        )
        cls.published = Icon.objects.create(
            unique_id="pub1", primary_tag="park", status=Icon.Status.PUBLISHED
        )
        cls.mine = Icon.objects.create(
            unique_id="mine1", status=Icon.Status.PENDING, created_by=cls.author
        )

    def listed_ids(self):
        response = self.client.get(reverse("icon-list"))
        return {row["unique_id"] for row in list_rows(response)}

    def test_anonymous_sees_only_published(self):
        self.assertEqual(self.listed_ids(), {"pub1"})

    def test_author_also_sees_their_own_submission(self):
        self.client.force_authenticate(self.author)
        self.assertEqual(self.listed_ids(), {"pub1", "mine1"})

    def test_a_fresh_submission_is_retrievable_by_its_author(self):
        # Used to 404: create() forced pending, but retrieve only showed published.
        self.client.force_authenticate(self.author)
        created = self.client.post(
            reverse("icon-list"), {"unique_id": "fresh1"}, format="json"
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.client.get(icon_url("fresh1")).status_code, status.HTTP_200_OK
        )

    def test_moderators_see_everything(self):
        self.client.force_authenticate(self.moderator)
        self.assertEqual(self.listed_ids(), {"pub1", "mine1"})

    def test_created_by_is_reported_and_not_client_settable(self):
        self.client.force_authenticate(self.author)
        response = self.client.post(
            reverse("icon-list"),
            {"unique_id": "owned1", "created_by": self.moderator.pk},
            format="json",
        )
        self.assertEqual(response.data["created_by"], "author")
        self.assertEqual(Icon.objects.get(unique_id="owned1").created_by, self.author)


class IconSearchTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        icon = Icon.objects.create(
            unique_id="pub1", primary_tag="park", status=Icon.Status.PUBLISHED
        )
        # Two tags both matching "green" on purpose: with one, the row can only be joined
        # once and the de-duplication claim below passes whether distinct() is there or not.
        icon.tags.set([
            Tag.objects.create(name="green"),
            Tag.objects.create(name="evergreen"),
        ])
        Icon.objects.create(
            unique_id="pub2", primary_tag="bench", status=Icon.Status.PUBLISHED
        )
        cls.author = in_role(
            User.objects.create_user("searcher", password="pw"), CONTRIBUTOR
        )
        # Matches every search term used below, but is not published.
        cls.hidden = Icon.objects.create(
            unique_id="park_draft",
            primary_tag="park",
            status=Icon.Status.PENDING,
            created_by=cls.author,
        )

    def ids(self, response):
        return sorted(row["unique_id"] for row in list_rows(response))

    def test_search_matches_primary_tag(self):
        response = self.client.get(reverse("icon-list"), {"q": "park"})
        self.assertEqual(self.ids(response), ["pub1"])

    def test_search_matches_secondary_tag_without_duplicating_rows(self):
        response = self.client.get(reverse("icon-list"), {"q": "green"})
        self.assertEqual(self.ids(response), ["pub1"])

    # Search and the visibility filter are composed, so this is the combination that
    # would leak: a term matching someone's unpublished row must not surface it.
    def test_search_cannot_surface_an_unpublished_row_anonymously(self):
        response = self.client.get(reverse("icon-list"), {"q": "park"})
        self.assertNotIn("park_draft", self.ids(response))

    def test_search_cannot_surface_another_users_unpublished_row(self):
        self.client.force_authenticate(
            in_role(User.objects.create_user("nosy", password="pw"), CONTRIBUTOR)
        )
        response = self.client.get(reverse("icon-list"), {"q": "park"})
        self.assertNotIn("park_draft", self.ids(response))

    def test_search_does_surface_your_own_unpublished_row(self):
        self.client.force_authenticate(self.author)
        response = self.client.get(reverse("icon-list"), {"q": "park"})
        self.assertIn("park_draft", self.ids(response))


class IconPaginationTests(APITestCase):
    """GET /api/icons/ must return page-sized payloads, not the full table."""

    @classmethod
    def setUpTestData(cls):
        for i in range(51):
            Icon.objects.create(
                unique_id=f"page{i:02d}",
                primary_tag="park" if i < 5 else "bench",
                status=Icon.Status.PUBLISHED,
            )

    def test_list_is_paginated_to_page_size(self):
        response = self.client.get(reverse("icon-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 51)
        self.assertEqual(len(response.data["results"]), 50)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

    def test_second_page_returns_the_remainder(self):
        response = self.client.get(reverse("icon-list"), {"page": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIsNotNone(response.data["previous"])
        self.assertIsNone(response.data["next"])

    def test_search_stays_paginated(self):
        response = self.client.get(reverse("icon-list"), {"q": "park"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 5)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertIn("results", response.data)


class HealthTests(APITestCase):
    def test_health_is_open_and_ok(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok"})


class RoleTests(APITestCase):
    """The role boundaries from docs/permissions.md that is_staff cannot express."""

    @classmethod
    def setUpTestData(cls):
        cls.no_role = User.objects.create_user("signed_in", password="pw")
        cls.contributor = in_role(
            User.objects.create_user("uploader", password="pw"), CONTRIBUTOR
        )
        cls.moderator = in_role(
            User.objects.create_user("curator", password="pw", is_staff=True), MODERATOR
        )
        cls.admin = in_role(
            User.objects.create_user("librarian", password="pw", is_staff=True), ADMIN
        )
        cls.superuser = User.objects.create_superuser("root", password="pw")

        cls.pending = Icon.objects.create(
            unique_id="queued1", status=Icon.Status.PENDING, created_by=cls.contributor
        )
        cls.published = Icon.objects.create(
            unique_id="live1", status=Icon.Status.PUBLISHED
        )

    def review(self, user, unique_id, new_status):
        self.client.force_authenticate(user)
        return self.client.post(
            icon_url(unique_id, "review"), {"status": new_status}, format="json"
        )

    # --- the groups themselves -----------------------------------------------------

    def test_the_three_role_groups_exist_with_permissions(self):
        for name, labels in ROLE_PERMISSIONS.items():
            group = Group.objects.get(name=name)
            held = {
                f"{perm.content_type.app_label}.{perm.codename}"
                for perm in group.permissions.all()
            }
            self.assertEqual(held, set(labels))

    # Moderators are deliberately denied auth.change_user: the admin's user form exposes
    # is_superuser and groups, so holding it would let them promote themselves to Admin
    # and take the publish right the API denies them.
    def test_only_admins_can_manage_accounts_in_the_django_admin(self):
        self.assertTrue(self.admin.has_perm("auth.change_user"))
        self.assertFalse(self.moderator.has_perm("auth.change_user"))
        self.assertFalse(self.contributor.has_perm("auth.change_user"))

    # An endpoint that forgets permission_classes must need a login for every action and a
    # role to write. Asserting which classes are attached is not enough -- that would pass
    # even if they allowed everything -- so check what the pair actually decides.
    def test_a_view_declaring_nothing_requires_a_login_and_a_role_to_write(self):
        class Bare(APIView):
            pass

        view = Bare()
        self.assertEqual(
            [type(perm) for perm in view.get_permissions()],
            [IsAuthenticated, IsContributorOrReadOnly],
        )

        factory = APIRequestFactory()

        def allows(method, user):
            request = Request(getattr(factory, method)("/anything"))
            request.user = user
            # Every class has to pass, which is what makes the pair stricter than either.
            return all(
                perm.has_permission(request, view) for perm in view.get_permissions()
            )

        # Anonymous gets nothing at all, reads included.
        self.assertFalse(allows("get", AnonymousUser()))
        self.assertFalse(allows("post", AnonymousUser()))

        # Signed in but in no group: a visitor who logged in, so read-only.
        self.assertTrue(allows("get", self.no_role))
        self.assertFalse(allows("post", self.no_role))
        self.assertFalse(allows("delete", self.no_role))

        # A role is what buys writes.
        self.assertTrue(allows("post", self.contributor))

    # The default demands a login, so anything meant to stay public has to say so itself.
    def test_health_stays_public_despite_the_login_default(self):
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get("/api/health/").status_code, status.HTTP_200_OK
        )

    # The icon endpoints declare their own classes, so the stricter default must not have
    # closed public browsing of the published library.
    def test_published_icons_are_still_readable_anonymously(self):
        self.client.force_authenticate(None)
        response = self.client.get(reverse("icon-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- upload is a role, not just a login ----------------------------------------

    def test_a_signed_in_user_with_no_role_cannot_upload(self):
        self.client.force_authenticate(self.no_role)
        response = self.client.post(
            reverse("icon-list"), {"unique_id": "probe1"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_a_signed_in_user_with_no_role_can_still_read(self):
        self.client.force_authenticate(self.no_role)
        response = self.client.get(icon_url("live1"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_a_contributor_can_upload(self):
        self.client.force_authenticate(self.contributor)
        response = self.client.post(
            reverse("icon-list"), {"unique_id": "probe2"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # Every Admin fixture only ever hit review/, whose permission_classes replace the
    # viewset's -- so nothing exercised an Admin through IsContributorOrReadOnly at all.
    def test_an_admin_has_full_crud_on_icons(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            reverse("icon-list"), {"unique_id": "adm1"}, format="json"
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self.client.patch(
                icon_url("adm1"), {"designer": "lib"}, format="json"
            ).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.delete(icon_url("adm1")).status_code, status.HTTP_204_NO_CONTENT
        )

    def test_a_superuser_can_upload(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.post(
            reverse("icon-list"), {"unique_id": "root1"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # --- the role -> permission policy is pinned to literals, not to itself ----------

    def test_role_permissions_match_the_documented_policy(self):
        expected = {
            CONTRIBUTOR: {
                "core.add_icon", "core.change_icon", "core.view_icon",
                "core.add_tag", "core.view_tag",
            },
            MODERATOR: {
                "core.add_icon", "core.change_icon", "core.delete_icon", "core.view_icon",
                "core.add_tag", "core.change_tag", "core.view_tag",
            },
            ADMIN: {
                "core.add_icon", "core.change_icon", "core.delete_icon", "core.view_icon",
                "core.add_tag", "core.change_tag", "core.delete_tag", "core.view_tag",
                "auth.add_user", "auth.change_user", "auth.view_user",
            },
        }
        self.assertEqual({k: set(v) for k, v in ROLE_PERMISSIONS.items()}, expected)
        # No role may hold auth rights except Admin, whatever else changes.
        for role in (CONTRIBUTOR, MODERATOR):
            self.assertFalse(
                any(label.startswith("auth.") for label in ROLE_PERMISSIONS[role]),
                f"{role} must not hold auth.* permissions",
            )

    # sync_roles uses set(), not add(), so a permission removed from the policy is
    # revoked from a group that already had it. A fresh test DB can't show that on its
    # own, so grant a stray permission first and check it is taken away.
    def test_sync_roles_revokes_a_permission_the_policy_no_longer_grants(self):
        from django.contrib.auth.models import Permission

        from .roles import sync_roles

        stray = Permission.objects.get(
            content_type__app_label="core", codename="delete_icon"
        )
        contributors = Group.objects.get(name=CONTRIBUTOR)
        contributors.permissions.add(stray)
        self.assertIn(stray, contributors.permissions.all())

        sync_roles()
        self.assertNotIn(stray, contributors.permissions.all())

    # --- approve != publish ---------------------------------------------------------

    def test_a_moderator_cannot_publish(self):
        response = self.review(self.moderator, "queued1", Icon.Status.PUBLISHED)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Icon.Status.PENDING)

    def test_a_moderator_can_approve_reject_and_request_changes(self):
        for outcome in (
            Icon.Status.APPROVED,
            Icon.Status.REJECTED,
            Icon.Status.CHANGES_REQUESTED,
        ):
            with self.subTest(outcome=outcome):
                response = self.review(self.moderator, "queued1", outcome)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.pending.refresh_from_db()
                self.assertEqual(self.pending.status, outcome)

    def test_an_admin_can_publish(self):
        response = self.review(self.admin, "queued1", Icon.Status.PUBLISHED)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Icon.Status.PUBLISHED)

    def test_a_superuser_is_treated_as_a_library_admin(self):
        response = self.review(self.superuser, "queued1", Icon.Status.PUBLISHED)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_a_contributor_cannot_review_at_all(self):
        response = self.review(self.contributor, "queued1", Icon.Status.APPROVED)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- staff is not a role --------------------------------------------------------

    def test_is_staff_alone_grants_nothing(self):
        # A moderator needs is_staff for the Django admin, so the API must not read
        # that flag, or admin access would imply the publish right.
        bare_staff = User.objects.create_user("bare", password="pw", is_staff=True)
        self.client.force_authenticate(bare_staff)
        self.assertEqual(
            self.client.post(
                reverse("icon-list"), {"unique_id": "probe3"}, format="json"
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.review(bare_staff, "queued1", Icon.Status.APPROVED).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    # --- moderators manage others' icons -------------------------------------------

    def test_a_moderator_can_delete_a_published_icon(self):
        self.client.force_authenticate(self.moderator)
        response = self.client.delete(icon_url("live1"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_a_moderator_sees_another_users_pending_icon(self):
        self.client.force_authenticate(self.moderator)
        self.assertEqual(
            self.client.get(icon_url("queued1")).status_code, status.HTTP_200_OK
        )


class ImportIconsStatusTests(TestCase):
    """The importer publishes on first load, but must not overrule a later review."""

    CSV = "unique-ID,designer,primary-tags,secondary-tags\nimp1,A Designer,park,green\n"

    def run_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_path = tmp / "meta.csv"
            csv_path.write_text(self.CSV, encoding="utf-8")
            (tmp / "png").mkdir()
            (tmp / "svg").mkdir()
            call_command(
                "import_icons",
                csv=str(csv_path),
                png=str(tmp / "png"),
                svg=str(tmp / "svg"),
                stdout=StringIO(),
            )

    def test_first_import_publishes(self):
        self.run_import()
        self.assertEqual(Icon.objects.get(unique_id="imp1").status, Icon.Status.PUBLISHED)

    def test_reimport_keeps_a_reviewers_decision_but_refreshes_metadata(self):
        self.run_import()
        icon = Icon.objects.get(unique_id="imp1")
        icon.status = Icon.Status.REJECTED
        icon.designer = ""
        icon.save(update_fields=["status", "designer"])

        self.run_import()
        icon.refresh_from_db()
        self.assertEqual(icon.status, Icon.Status.REJECTED)   # not republished
        self.assertEqual(icon.designer, "A Designer")         # metadata still updated


class AdminSideDoorTests(TestCase):
    """The Django admin does not run DRF's permission classes, so the role rules have to
    be enforced there separately. Moderators get is_staff to review, which means the icon
    change form is reachable to them."""

    @classmethod
    def setUpTestData(cls):
        cls.moderator = in_role(
            User.objects.create_user("admin_mod", password="pw", is_staff=True), MODERATOR
        )
        cls.admin = in_role(
            User.objects.create_user("admin_lib", password="pw", is_staff=True), ADMIN
        )

    def change_url(self, icon):
        return django_reverse("admin:core_icon_change", args=[icon.pk])

    def post_change(self, user, icon, **overrides):
        self.client.force_login(user)
        form = {
            field: ""
            for field in (
                "designer", "metadata_source", "uploader", "primary_tag", "when_created",
                "when_uploaded", "where_created", "icon_geography", "icon_description",
                "icon_context", "creation_context", "notes",
            )
        }
        form["unique_id"] = icon.unique_id
        form.update(overrides)
        return self.client.post(self.change_url(icon), form)

    def test_a_moderator_cannot_publish_through_the_admin_form(self):
        icon = Icon.objects.create(unique_id="sd1", status=Icon.Status.PENDING)
        response = self.post_change(self.moderator, icon, status=Icon.Status.PUBLISHED)
        self.assertEqual(response.status_code, 302)  # the form itself saves fine
        icon.refresh_from_db()
        self.assertEqual(icon.status, Icon.Status.PENDING)  # status was ignored

    def test_a_moderator_cannot_reassign_authorship_through_the_admin_form(self):
        owner = User.objects.create_user("admin_owner", password="pw")
        icon = Icon.objects.create(
            unique_id="sd2", status=Icon.Status.PENDING, created_by=owner
        )
        self.post_change(self.moderator, icon, created_by=self.moderator.pk)
        icon.refresh_from_db()
        self.assertEqual(icon.created_by, owner)

    def test_a_moderator_can_still_edit_the_fields_they_should(self):
        icon = Icon.objects.create(unique_id="sd3", status=Icon.Status.PENDING)
        self.post_change(self.moderator, icon, designer="tidied by a mod")
        icon.refresh_from_db()
        self.assertEqual(icon.designer, "tidied by a mod")

    def test_an_icon_a_moderator_adds_in_the_admin_starts_pending(self):
        self.client.force_login(self.moderator)
        self.client.post(
            django_reverse("admin:core_icon_add"),
            {"unique_id": "sd4", "status": Icon.Status.PUBLISHED, "designer": "",
             "metadata_source": "", "uploader": "", "primary_tag": "", "when_created": "",
             "when_uploaded": "", "where_created": "", "icon_geography": "",
             "icon_description": "", "icon_context": "", "creation_context": "", "notes": ""},
        )
        self.assertEqual(Icon.objects.get(unique_id="sd4").status, Icon.Status.PENDING)

    def test_a_library_admin_can_publish_through_the_admin_form(self):
        icon = Icon.objects.create(unique_id="sd5", status=Icon.Status.APPROVED)
        self.post_change(self.admin, icon, status=Icon.Status.PUBLISHED)
        icon.refresh_from_db()
        self.assertEqual(icon.status, Icon.Status.PUBLISHED)


class ContributorApprovalTests(TestCase):
    """Issue #15: granting upload rights must not go through Django's user form, which
    also edits is_superuser and groups and so can hand over the publish right."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = in_role(
            User.objects.create_user("approver", password="pw", is_staff=True), ADMIN
        )
        cls.moderator = in_role(
            User.objects.create_user("reviewer", password="pw", is_staff=True), MODERATOR
        )
        cls.applicant = User.objects.create_user("applicant", password="pw")

    def run_action(self, actor, action, *targets):
        self.client.force_login(actor)
        return self.client.post(
            django_reverse("admin:auth_user_changelist"),
            {
                "action": action,
                "index": 0,
                "_selected_action": [str(user.pk) for user in targets],
            },
        )

    def offered_actions(self, user):
        request = APIRequestFactory().get("/admin/auth/user/")
        request.user = user
        return set(UserAdmin(User, admin.site).get_actions(request))

    def can_upload(self, user, unique_id):
        client = APIClient()
        client.force_authenticate(user)
        response = client.post(
            reverse("icon-list"), {"unique_id": unique_id}, format="json"
        )
        return response.status_code == status.HTTP_201_CREATED

    # --- the done criteria ----------------------------------------------------------

    def test_an_admin_can_grant_contributor_access_and_the_user_can_then_upload(self):
        self.assertFalse(self.can_upload(self.applicant, "pre1"))
        self.run_action(self.admin, "grant_contributor_access", self.applicant)
        self.assertTrue(self.can_upload(self.applicant, "post1"))

    # The reason the action exists instead of auth.change_user: the user form could do
    # both of these, so assert the action leaves everything but one group alone.
    def test_the_action_cannot_grant_superuser_staff_or_any_other_role(self):
        self.run_action(self.admin, "grant_contributor_access", self.applicant)
        self.applicant.refresh_from_db()
        self.assertFalse(self.applicant.is_superuser)
        self.assertFalse(self.applicant.is_staff)
        self.assertEqual(
            set(self.applicant.groups.values_list("name", flat=True)), {CONTRIBUTOR}
        )
        self.assertEqual(self.applicant.user_permissions.count(), 0)

    def test_revoking_contributor_access_takes_upload_back(self):
        self.run_action(self.admin, "grant_contributor_access", self.applicant)
        self.run_action(self.admin, "revoke_contributor_access", self.applicant)
        self.assertFalse(self.applicant.groups.filter(name=CONTRIBUTOR).exists())
        self.assertFalse(self.can_upload(self.applicant, "post2"))

    # Revoke must not quietly strip the other roles off a moderator or admin who also
    # happens to sit in Contributor.
    def test_revoking_leaves_a_users_other_roles_in_place(self):
        in_role(self.moderator, CONTRIBUTOR)
        self.run_action(self.admin, "revoke_contributor_access", self.moderator)
        self.assertEqual(
            set(self.moderator.groups.values_list("name", flat=True)), {MODERATOR}
        )

    # --- who gets the actions -------------------------------------------------------

    def test_a_library_admin_is_offered_both_actions(self):
        self.assertLessEqual(
            {"grant_contributor_access", "revoke_contributor_access"},
            self.offered_actions(self.admin),
        )

    # Moderators are the role the matrix would like to do this, but the website approval
    # page comes later -- until then they must not reach it through the admin at all.
    def test_a_moderator_is_not_offered_the_actions_and_cannot_post_one(self):
        self.assertEqual(
            {"grant_contributor_access", "revoke_contributor_access"}
            & self.offered_actions(self.moderator),
            set(),
        )
        self.run_action(self.moderator, "grant_contributor_access", self.applicant)
        self.assertFalse(self.applicant.groups.exists())

    # The changelist is the only way in, and reaching it needs auth.view_user, which
    # only the Admin group holds. Belt and braces with the get_actions gate above.
    def test_the_user_changelist_is_closed_to_moderators(self):
        self.client.force_login(self.moderator)
        response = self.client.get(django_reverse("admin:auth_user_changelist"))
        self.assertEqual(response.status_code, 403)  # staff, but no auth.view_user

    # --- bulk and no-op behaviour ---------------------------------------------------

    def test_granting_is_idempotent_and_reports_only_real_changes(self):
        already = in_role(User.objects.create_user("veteran", password="pw"), CONTRIBUTOR)
        response = self.run_action(
            self.admin, "grant_contributor_access", already, self.applicant
        )
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertEqual(messages, ["applicant can now upload icons."])
        self.assertEqual(
            already.groups.filter(name=CONTRIBUTOR).count(), 1
        )  # not doubled


def minimal_png():
    """A real 1x1 PNG, built here so the bytes in these tests are honest ones."""

    def chunk(kind, payload):
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)  # 1x1, 8-bit greyscale
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"\x00\x00"))
        + chunk(b"IEND", b"")
    )


MINIMAL_SVG = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<!-- a feminist map icon -->\n'
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect width="1" height="1"/></svg>'
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="icon-upload-tests-"))
class IconUploadValidationTests(APITestCase):
    """Issue #16: the API does not trust what a contributor attaches."""

    @classmethod
    def setUpTestData(cls):
        cls.author = in_role(User.objects.create_user("uploader", password="pw"), CONTRIBUTOR)

    def setUp(self):
        self.client.force_authenticate(self.author)

    def upload(self, **files):
        return self.client.post(
            reverse("icon-list"),
            {"unique_id": "upload1", **files},
            format="multipart",
        )

    def media_files(self):
        root = Path(settings.MEDIA_ROOT)
        return sorted(p.name for p in root.rglob("*") if p.is_file())

    # --- the happy path -------------------------------------------------------------

    def test_a_real_png_and_svg_are_accepted(self):
        response = self.upload(
            png_file=SimpleUploadedFile("icon.png", minimal_png(), content_type="image/png"),
            svg_file=SimpleUploadedFile("icon.svg", MINIMAL_SVG, content_type="image/svg+xml"),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        icon = Icon.objects.get(unique_id="upload1")
        self.assertTrue(icon.png_file)
        self.assertTrue(icon.svg_file)

    def test_an_svg_opening_straight_with_the_root_element_is_accepted(self):
        """No XML declaration, no comment -- still a valid SVG."""
        response = self.upload(
            svg_file=SimpleUploadedFile(
                "icon.svg", b'<svg xmlns="http://www.w3.org/2000/svg"/>', content_type="image/svg+xml"
            )
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_an_svg_with_a_multibyte_character_on_the_read_boundary_is_accepted(self):
        """The type check reads a fixed number of bytes; the cut can land mid-character."""
        prefix = b'<svg xmlns="http://www.w3.org/2000/svg"><title>'
        head = prefix + b"a" * (4095 - len(prefix))  # em dash straddles byte 4096
        svg = head + "\u2014".encode() + b"</title></svg>"
        response = self.upload(
            svg_file=SimpleUploadedFile("boundary.svg", svg, content_type="image/svg+xml")
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_an_svg_with_invalid_utf8_bytes_is_still_rejected(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><title>\xff\xfe</title></svg>'
        response = self.upload(
            svg_file=SimpleUploadedFile("broken.svg", svg, content_type="image/svg+xml")
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("svg_file", response.data)

    # --- the extension is not enough -----------------------------------------------

    def test_a_png_renamed_as_svg_is_rejected(self):
        response = self.upload(
            svg_file=SimpleUploadedFile("icon.svg", minimal_png(), content_type="image/svg+xml")
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("svg_file", response.data)

    def test_text_renamed_as_png_is_rejected(self):
        response = self.upload(
            png_file=SimpleUploadedFile("icon.png", b"not a png at all", content_type="image/png")
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("png_file", response.data)

    def test_an_html_page_claiming_to_be_an_svg_is_rejected(self):
        response = self.upload(
            svg_file=SimpleUploadedFile(
                "icon.svg", b"<html><body><svg/></body></html>", content_type="image/svg+xml"
            )
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("svg_file", response.data)

    # --- the wrong format entirely --------------------------------------------------

    def test_a_jpeg_is_rejected(self):
        response = self.upload(
            png_file=SimpleUploadedFile(
                "icon.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 64, content_type="image/jpeg"
            )
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("png_file", response.data)

    def test_a_gif_renamed_as_png_is_rejected(self):
        response = self.upload(
            png_file=SimpleUploadedFile("icon.png", b"GIF89a" + b"\x00" * 64, content_type="image/png")
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("png_file", response.data)

    # --- the size limit -------------------------------------------------------------

    def test_a_png_over_the_size_limit_is_rejected(self):
        oversize = minimal_png() + b"\x00" * MAX_ICON_FILE_SIZE
        response = self.upload(
            png_file=SimpleUploadedFile("icon.png", oversize, content_type="image/png")
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("png_file", response.data)

    def test_an_svg_over_the_size_limit_is_rejected(self):
        oversize = MINIMAL_SVG + b"<!--" + b"x" * MAX_ICON_FILE_SIZE + b"-->"
        response = self.upload(
            svg_file=SimpleUploadedFile("icon.svg", oversize, content_type="image/svg+xml")
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("svg_file", response.data)

    def test_a_png_exactly_at_the_size_limit_is_accepted(self):
        png = minimal_png()
        padded = png + b"\x00" * (MAX_ICON_FILE_SIZE - len(png))
        response = self.upload(
            png_file=SimpleUploadedFile("icon.png", padded, content_type="image/png")
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    # --- replacing a file is an upload too ------------------------------------------

    def test_swapping_in_a_bad_file_on_patch_is_rejected(self):
        """The check is on the field, so it covers a replacement, not just a create."""
        self.upload(
            png_file=SimpleUploadedFile("icon.png", minimal_png(), content_type="image/png")
        )
        original = Icon.objects.get(unique_id="upload1").png_file.name
        response = self.client.patch(
            icon_url("upload1"),
            {"png_file": SimpleUploadedFile("swap.png", b"nope", content_type="image/png")},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Icon.objects.get(unique_id="upload1").png_file.name, original)

    def test_patching_other_fields_does_not_recheck_the_stored_file(self):
        """An untouched file is not re-read, so a missing media file cannot block an edit."""
        icon = Icon.objects.create(
            unique_id="upload1", png_file="icons/png/not-on-disk.png", created_by=self.author
        )
        response = self.client.patch(
            icon_url("upload1"), {"primary_tag": "bench"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        icon.refresh_from_db()
        self.assertEqual(icon.png_file.name, "icons/png/not-on-disk.png")

    # --- nothing rejected reaches the disk ------------------------------------------

    def test_a_rejected_upload_writes_nothing_under_media(self):
        before = self.media_files()
        response = self.upload(
            png_file=SimpleUploadedFile("evil.png", b"<?php ?>", content_type="image/png")
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.media_files(), before)
        self.assertFalse(Icon.objects.filter(unique_id="upload1").exists())

    # --- the files already on disk are left alone -----------------------------------

    def test_import_icons_rows_are_not_revalidated(self):
        """Model.save() does not run validators, so imported paths stay as they are."""
        icon = Icon.objects.create(
            unique_id="imported1",
            png_file="icons/png/imported1.png",
            svg_file="icons/svg/imported1.svg",
        )
        icon.refresh_from_db()
        self.assertEqual(icon.png_file.name, "icons/png/imported1.png")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="icon-media-tests-"))
class IconMediaAccessTests(APITestCase):
    """Issue #18: the PNG/SVG of an unpublished icon must be as invisible as its row.

    Before this, every file under MEDIA_ROOT was served at a guessable /media/ path with
    no check at all, so the row-level rules the other tests here prove were one filename
    away from being bypassed."""

    @classmethod
    def setUpTestData(cls):
        cls.author = in_role(User.objects.create_user("mediaowner", password="pw"), CONTRIBUTOR)
        cls.other = in_role(User.objects.create_user("mediaother", password="pw"), CONTRIBUTOR)
        cls.moderator = in_role(
            User.objects.create_user("mediamod", password="pw", is_staff=True), MODERATOR
        )

        cls.published = Icon.objects.create(
            unique_id="pubmedia",
            primary_tag="park",
            status=Icon.Status.PUBLISHED,
            png_file=SimpleUploadedFile("pub.png", minimal_png(), content_type="image/png"),
            svg_file=SimpleUploadedFile("pub.svg", MINIMAL_SVG, content_type="image/svg+xml"),
        )
        # In the review queue, so its files are readable by its author and moderators only.
        cls.pending = Icon.objects.create(
            unique_id="pendmedia",
            primary_tag="bench",
            status=Icon.Status.PENDING,
            created_by=cls.author,
            png_file=SimpleUploadedFile("pend.png", minimal_png(), content_type="image/png"),
            svg_file=SimpleUploadedFile("pend.svg", MINIMAL_SVG, content_type="image/svg+xml"),
        )
        # Published, but metadata only -- plenty of the imported rows look like this.
        cls.fileless = Icon.objects.create(
            unique_id="nomedia",
            primary_tag="well",
            status=Icon.Status.PUBLISHED,
        )

    def fetch(self, user, unique_id, kind, **extra):
        if user is not None:
            self.client.force_authenticate(user)
        return self.client.get(icon_url(unique_id, kind), **extra)

    def body(self, response):
        return b"".join(response.streaming_content)

    # --- published files stay public ------------------------------------------------

    def test_a_published_png_is_served_to_anyone(self):
        response = self.fetch(None, "pubmedia", "png")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(self.body(response), minimal_png())

    def test_a_published_svg_is_served_to_anyone(self):
        response = self.fetch(None, "pubmedia", "svg")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/svg+xml")
        self.assertEqual(self.body(response), MINIMAL_SVG)

    def test_a_client_asking_precisely_for_image_png_is_still_served(self):
        """DRF negotiates a renderer before the handler; JSON is the only one configured."""
        response = self.fetch(None, "pubmedia", "png", HTTP_ACCEPT="image/png")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- unpublished files are not -------------------------------------------------

    def test_a_pending_icons_png_is_not_public(self):
        response = self.fetch(None, "pendmedia", "png")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_a_pending_icons_svg_is_not_public(self):
        response = self.fetch(None, "pendmedia", "svg")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_another_contributor_cannot_read_a_pending_icons_file(self):
        """404, not 403: the row itself is invisible, so saying "forbidden" would confirm
        that an icon with that id exists."""
        response = self.fetch(self.other, "pendmedia", "png")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_the_owner_can_read_their_own_pending_file(self):
        response = self.fetch(self.author, "pendmedia", "png")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.body(response), minimal_png())

    def test_a_moderator_can_read_a_pending_file_for_review(self):
        response = self.fetch(self.moderator, "pendmedia", "svg")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.body(response), MINIMAL_SVG)

    def test_a_file_withdrawn_from_publication_stops_being_public(self):
        """The check reads the row's status at request time, not at upload time."""
        self.published.status = Icon.Status.CHANGES_REQUESTED
        self.published.save(update_fields=["status"])
        self.assertEqual(
            self.fetch(None, "pubmedia", "png").status_code, status.HTTP_404_NOT_FOUND
        )

    # --- the raw /media/ path is gone ----------------------------------------------

    @override_settings(DEBUG=True)
    def test_the_raw_media_path_is_not_served_even_with_debug_on(self):
        """static() under DEBUG was the hole: it published MEDIA_ROOT with no checks."""
        response = self.client.get(settings.MEDIA_URL + self.pending.png_file.name)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_the_detail_response_points_at_the_gated_endpoint(self):
        response = self.client.get(icon_url("pubmedia"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["png_file"].endswith("/api/icons/pubmedia/png/"))
        self.assertTrue(response.data["svg_file"].endswith("/api/icons/pubmedia/svg/"))

    def test_no_response_hands_out_a_media_path(self):
        for url in (reverse("icon-list"), icon_url("pubmedia")):
            with self.subTest(url=url):
                self.assertNotIn(b"/media/", self.client.get(url).content)

    def test_an_icon_with_no_file_reports_null_rather_than_a_url(self):
        response = self.client.get(icon_url("nomedia"))
        self.assertIsNone(response.data["png_file"])
        self.assertIsNone(response.data["svg_file"])

    # --- how the bytes are sent -----------------------------------------------------

    def test_an_svg_is_served_as_a_download(self):
        """An SVG can carry a <script>; inline on this origin it would run with the API's
        own session cookie. An <img src> renders it regardless, and runs no script."""
        response = self.fetch(None, "pubmedia", "svg")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_a_png_is_served_inline(self):
        response = self.fetch(None, "pubmedia", "png")
        self.assertNotIn("attachment", response.get("Content-Disposition", ""))

    def test_an_unpublished_file_is_kept_out_of_shared_caches(self):
        response = self.fetch(self.author, "pendmedia", "png")
        self.assertIn("no-store", response["Cache-Control"])

    def test_a_published_file_is_left_cacheable(self):
        response = self.fetch(None, "pubmedia", "png")
        self.assertNotIn("no-store", response.get("Cache-Control", ""))

    # --- the endpoints are read-only ------------------------------------------------

    def test_an_icon_with_no_png_is_a_404(self):
        self.assertEqual(
            self.fetch(None, "nomedia", "png").status_code, status.HTTP_404_NOT_FOUND
        )

    def test_a_row_whose_file_vanished_from_storage_is_a_404_not_a_500(self):
        Path(self.published.png_file.path).unlink()
        self.assertEqual(
            self.fetch(None, "pubmedia", "png").status_code, status.HTTP_404_NOT_FOUND
        )

    def test_the_file_endpoints_do_not_accept_writes(self):
        self.client.force_authenticate(self.author)
        response = self.client.post(icon_url("pendmedia", "png"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
