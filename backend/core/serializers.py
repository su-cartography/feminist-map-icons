from rest_framework import serializers
from rest_framework.reverse import reverse

from .models import Icon, Tag


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

    # POST: create a new icon
    def create(self, validated_data):
        tag_names = validated_data.pop("tag_names", None)
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
