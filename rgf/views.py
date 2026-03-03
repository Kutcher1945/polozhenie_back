import tempfile
from pathlib import Path

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import ImportFileSerializer, PreviewFileSerializer, DeleteRecordsSerializer
from . import services
from .planning_api import org_mapping
from .planning_api.auth import login
from .planning_api.rgf_api import get_gu_list
from .planning_api.config import IIN, PASSWORD


class OrganizationsView(APIView):
    """GET /api/rgf/organizations/ — list all GU organizations"""

    @swagger_auto_schema(
        operation_summary="List all GU organizations",
        responses={200: openapi.Response("List of organizations", schema=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                "id": openapi.Schema(type=openapi.TYPE_STRING),
                "name": openapi.Schema(type=openapi.TYPE_STRING),
            })
        ))}
    )
    def get(self, request):
        try:
            orgs = services.list_organizations()
            return Response(orgs)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class PreviewView(APIView):
    """POST /api/rgf/preview/ — parse a .docx and return extracted data without importing"""
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Preview document parsing",
        operation_description="Parse a .docx file and return extracted data + auto-detected org. Does NOT import.",
        manual_parameters=[
            openapi.Parameter("file", openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
        ],
        responses={200: openapi.Response("Parsed data preview")}
    )
    def post(self, request):
        serializer = PreviewFileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file_obj = request.FILES["file"]
        filename = file_obj.name

        if not filename.endswith(".docx"):
            return Response({"error": "Only .docx files are supported"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token, _ = login(IIN, PASSWORD)
            full_gu_list = get_gu_list(token) or []

            result = services.preview_document(file_obj.read(), filename, full_gu_list)
            return Response(result)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImportView(APIView):
    """POST /api/rgf/import/ — upload + import one or more .docx files"""
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Import .docx files",
        operation_description=(
            "Upload one or more .docx files. Each file is parsed and imported to planning.gov.kz. "
            "Organization is auto-detected from filename or document content unless gu_id is provided."
        ),
        manual_parameters=[
            openapi.Parameter("files", openapi.IN_FORM, type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_FILE), required=True),
            openapi.Parameter("gu_id", openapi.IN_FORM, type=openapi.TYPE_STRING, required=False,
                              description="Force a specific GU ID for all files"),
        ],
        responses={200: openapi.Response("Import results per file")}
    )
    def post(self, request):
        files = request.FILES.getlist("files")
        forced_gu_id = request.data.get("gu_id", "").strip() or None

        if not files:
            return Response({"error": "No files provided"}, status=status.HTTP_400_BAD_REQUEST)

        invalid = [f.name for f in files if not f.name.endswith(".docx")]
        if invalid:
            return Response({"error": f"Only .docx files are supported: {invalid}"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            token, _ = login(IIN, PASSWORD)
            full_gu_list = get_gu_list(token) or []
        except Exception as e:
            return Response({"error": f"Auth failed: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        results = []
        for file_obj in files:
            filename = file_obj.name
            file_bytes = file_obj.read()

            gu_id = forced_gu_id
            gu_name = None
            if not gu_id:
                with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                    tmp.write(file_bytes)
                    tmp_path = Path(tmp.name)
                try:
                    gu_id, gu_name, detected_source = org_mapping.suggest_gu_for_file(
                        filename, full_gu_list, tmp_path
                    )
                finally:
                    tmp_path.unlink(missing_ok=True)

            if not gu_id:
                results.append({
                    "filename": filename,
                    "status": "skipped",
                    "skip_reason": "Could not auto-detect organization. Provide gu_id manually.",
                })
                continue

            result = services.import_document(file_bytes, filename, gu_id, token)
            if gu_name:
                result["gu_name"] = gu_name
            results.append(result)

        summary = {
            "total": len(results),
            "success": sum(1 for r in results if r["status"] == "success"),
            "skipped": sum(1 for r in results if r["status"] == "skipped"),
            "error": sum(1 for r in results if r["status"] == "error"),
        }

        return Response({"summary": summary, "results": results})


class RecordsView(APIView):
    """GET /api/rgf/records/ — list all previously imported records"""

    @swagger_auto_schema(
        operation_summary="List imported records",
        operation_description="Returns all records found in local import report files.",
        responses={200: openapi.Response("List of imported records")}
    )
    def get(self, request):
        records = services.get_imported_records()
        return Response({"total": len(records), "records": records})


class DeleteRecordsView(APIView):
    """DELETE /api/rgf/records/ — delete specific or all records"""

    @swagger_auto_schema(
        operation_summary="Delete records",
        operation_description=(
            "Delete records by ID list. "
            "If record_ids is empty and confirm=true, deletes ALL records from import reports."
        ),
        request_body=DeleteRecordsSerializer,
        responses={200: openapi.Response("Deletion result")}
    )
    def delete(self, request):
        serializer = DeleteRecordsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if not serializer.validated_data["confirm"]:
            return Response({"error": "confirm must be true"}, status=status.HTTP_400_BAD_REQUEST)

        record_ids = serializer.validated_data.get("record_ids") or []

        if not record_ids:
            all_records = services.get_imported_records()
            record_ids = [r["record_id"] for r in all_records]

        if not record_ids:
            return Response({"message": "No records found to delete", "deleted": [], "failed": []})

        try:
            token = services.get_token()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        result = services.delete_records(record_ids, token)
        return Response({
            "total": len(record_ids),
            "deleted_count": len(result["deleted"]),
            "failed_count": len(result["failed"]),
            "deleted": result["deleted"],
            "failed": result["failed"],
        })
