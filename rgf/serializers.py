from rest_framework import serializers


class ImportFileSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        help_text="List of .docx files to import"
    )
    gu_id = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Force a specific GU ID for all files (optional, auto-detected if omitted)"
    )


class PreviewFileSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="Single .docx file to preview")


class DeleteRecordsSerializer(serializers.Serializer):
    record_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of record IDs to delete. If empty, deletes ALL records from reports."
    )
    confirm = serializers.BooleanField(
        help_text="Must be true to confirm deletion"
    )
