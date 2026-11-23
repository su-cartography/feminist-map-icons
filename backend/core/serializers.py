import secrets

from rest_framework import serializers
from rest_framework.reverse import reverse

from .models import ContributorAccessRequest, Icon, Tag


# Turns a Tag database row into JSON (and back).
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


# Turns an Icon database row into JSON for the API.
class IconSerializer(serializers.ModelSerializer):
    # When reading: send linked secondary tags as [{id, name}, ...]
    tags = TagSerializer(many=True, read_only=True)
    # When writing: accept a simple list like ["star", "POI"] 
    tag_names = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
    )
    # When reading: the uploader's username, or null for imported rows.
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Icon
        fields = [
            "unique_id",
            "designer",
            "metadata_source",
            "uploader",
            "primary_tag",
            "tags",
            "tag_names",
            "when_created",
            "when_uploaded",
            "where_created",
            "icon_geography",
            "icon_description",
            "icon_context",
            "creation_context",
            "notes",
            "status",
            "png_file",
            "svg_file",
            "created_by",
            "created_at",
            "updated_at",
        ]
        # status is read-only on purpose: a check only in create() is one PATCH away
        # from being skipped. It moves through the submit/review actions instead.
        read_only_fields = ["status", "created_at", "updated_at"]
        # Clients may omit unique_id; create() fills an 8-hex id to match the library.
        extra_kwargs = {
            "unique_id": {"required": False, "allow_blank": True},
        }

    # Find or create Tag rows, then link them to this icon (replaces old secondary tags)
    def _set_tags(self, icon, tag_names):
        if tag_names is None:
            return
        tags = []
        for name in tag_names:
            name = name.strip()
            if not name:
                continue
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        icon.tags.set(tags)

    def _allocate_unique_id(self):
        # Same shape as imported Zenodo ids (e.g. 00e8059e): 8 lowercase hex chars.
        for _ in range(32):
            candidate = secrets.token_hex(4)
            if not Icon.objects.filter(unique_id=candidate).exists():
                return candidate
        raise serializers.ValidationError(
            {"unique_id": "Could not allocate a unique id. Try again."}
        )

    # POST: create a new icon
    def create(self, validated_data):
        tag_names = validated_data.pop("tag_names", None)
        unique_id = (validated_data.get("unique_id") or "").strip()
        if unique_id:
            validated_data["unique_id"] = unique_id
        else:
            validated_data["unique_id"] = self._allocate_unique_id()
        # New uploads still start as pending (waiting for review); that is the model
        # default now that status is read-only here.
        icon = Icon.objects.create(**validated_data)
        self._set_tags(icon, tag_names)
        return icon

    # PUT/PATCH: update an existing icon
    def update(self, instance, validated_data):
        tag_names = validated_data.pop("tag_names", None)
        icon = super().update(instance, validated_data)
        self._set_tags(icon, tag_names)
        return icon

    # Reading: hand out the gated file URLs, never the raw MEDIA_URL path the FileField
    # would produce by itself. The field names stay as they are -- a client still finds 
    # the file under "png_file".
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["png_file"] = self._file_url(instance, "png")
        data["svg_file"] = self._file_url(instance, "svg")
        return data

    def _file_url(self, instance, kind):
        
        if not getattr(instance, f"{kind}_file"):
            return None
        
        return reverse(
            f"icon-{kind}",
            kwargs={"unique_id": instance.unique_id},
            request=self.context.get("request"),
        )


# Body of POST /api/icons/<unique_id>/review/
class IconStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Icon.Status.choices)


class ContributorAccessRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContributorAccessRequest
        fields = ["id", "status", "note", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class MeSerializer(serializers.Serializer):
    username = serializers.CharField()
    is_contributor = serializers.BooleanField()
    access_request = ContributorAccessRequestSerializer(allow_null=True)


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    def validate_username(self, value):
        from django.contrib.auth.models import User

        username = value.strip()
        if not username:
            raise serializers.ValidationError("Username is required.")
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("That username is already taken.")
        return username

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        from django.contrib.auth.models import User

        full_name = (validated_data.get("full_name") or "").strip()
        # No Contributor (or any) group here — upload rights come only after admin grant.
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"].strip(),
            password=validated_data["password"],
            first_name=full_name[:150],
        )
