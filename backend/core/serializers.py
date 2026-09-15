from rest_framework import serializers
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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

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
        # New uploads always start as pending (waiting for review)
        validated_data["status"] = Icon.Status.PENDING
        icon = Icon.objects.create(**validated_data)
        self._set_tags(icon, tag_names)
        return icon

    # PUT/PATCH: update an existing icon
    def update(self, instance, validated_data):
        tag_names = validated_data.pop("tag_names", None)
        icon = super().update(instance, validated_data)
        self._set_tags(icon, tag_names)
        return icon
