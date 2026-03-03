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
from .planning_api.config import IIN, PASSWORD
from .models import AuditLog, ImportRecord


def _log(action, filename='', gu_id='', gu_name='', status_val='', details=None):
    """Fire-and-forget audit log entry."""
    try:
        AuditLog.objects.create(
            action=action,
            filename=filename,
            gu_id=gu_id,
            gu_name=gu_name,
            status=status_val,
            details=details or {},
        )
    except Exception:
        pass


class AuthView(APIView):
    """POST /api/rgf/auth/ — verify login + password"""

    def post(self, request):
        login_input = request.data.get('login', '')
        password = request.data.get('password', '')
        if login_input == IIN and password == PASSWORD:
            _log('login', status_val='success')
            return Response({"success": True})
        _log('login', status_val='error', details={'reason': 'wrong credentials'})
        return Response({"error": "Неверный логин или пароль"}, status=status.HTTP_401_UNAUTHORIZED)


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
            _, full_gu_list = services.get_cached_auth()
            result = services.preview_document(file_obj.read(), filename, full_gu_list)
            _log('preview',
                 filename=filename,
                 gu_id=result.get('gu_id', ''),
                 gu_name=result.get('gu_name', ''),
                 status_val='success',
                 details={'issues': result.get('issues', []), 'warnings': result.get('warnings', [])})
            return Response(result)
        except Exception as e:
            _log('preview', filename=filename, status_val='error', details={'error': str(e)})
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
            token, full_gu_list = services.get_cached_auth()
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
                result = {
                    "filename": filename,
                    "status": "skipped",
                    "skip_reason": "Could not auto-detect organization. Provide gu_id manually.",
                }
                _log('import', filename=filename, status_val='skipped',
                     details={'skip_reason': result['skip_reason']})
                results.append(result)
                continue

            result = services.import_document(file_bytes, filename, gu_id, token)
            if gu_name:
                result["gu_name"] = gu_name
            _log('import', filename=filename, gu_id=gu_id, gu_name=gu_name or '',
                 status_val=result.get('status', ''),
                 details={k: v for k, v in result.items() if k not in ('filename',)})
            results.append(result)

        summary = {
            "total": len(results),
            "success": sum(1 for r in results if r["status"] == "success"),
            "skipped": sum(1 for r in results if r["status"] == "skipped"),
            "error": sum(1 for r in results if r["status"] == "error"),
        }

        return Response({"summary": summary, "results": results})


class ImportParsedView(APIView):
    """POST /api/rgf/import-parsed/ — import pre-edited parsed data (no file upload)"""

    def post(self, request):
        gu_id = request.data.get('gu_id', '').strip()
        if not gu_id:
            return Response({"error": "gu_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        filename = request.data.get('filename', '')
        gu_name = request.data.get('gu_name', '')
        data = {
            "general_provisions":           request.data.get('general_provisions', ''),
            "tasks":                        request.data.get('tasks', []),
            "authorities_rights":           request.data.get('authorities_rights', []),
            "authorities_responsibilities": request.data.get('authorities_responsibilities', []),
            "functions":                    request.data.get('functions', []),
            "additions":                    request.data.get('additions', ''),
        }

        try:
            token, _ = services.get_cached_auth()
            result = services.import_parsed(gu_id, data, token, gu_name=gu_name)
            _log('import', filename=filename, gu_id=gu_id,
                 status_val=result.get('status', ''),
                 details={**result, 'was_edited': True})
            return Response(result)
        except Exception as e:
            _log('import', filename=filename, gu_id=gu_id, status_val='error', details={'error': str(e)})
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RecordsView(APIView):
    """GET /api/rgf/records/ — list all previously imported records (from DB)"""

    @swagger_auto_schema(
        operation_summary="List imported records",
        operation_description="Returns all import records stored in the database.",
        responses={200: openapi.Response("List of imported records")}
    )
    def get(self, request):
        qs = ImportRecord.objects.all()
        records = []
        for r in qs:
            records.append({
                "id":                      r.id,
                "record_id":               r.record_id,
                "filename":                r.filename,
                "gu_id":                   r.gu_id,
                "gu_name":                 r.gu_name,
                "status":                  r.status,
                "skip_reason":             r.skip_reason,
                "error":                   r.error,
                "url":                     r.url,
                "was_edited":              r.was_edited,
                "tasks_count":             r.tasks_count,
                "rights_count":            r.rights_count,
                "responsibilities_count":  r.responsibilities_count,
                "functions_count":         r.functions_count,
                "created_at":              r.created_at.isoformat(),
            })
        return Response({"total": len(records), "records": records})


class AuditLogView(APIView):
    """GET /api/rgf/audit/ — return recent audit log entries"""

    def get(self, request):
        qs = AuditLog.objects.all()[:500]
        entries = []
        for e in qs:
            entries.append({
                "id":         e.id,
                "action":     e.action,
                "filename":   e.filename,
                "gu_id":      e.gu_id,
                "gu_name":    e.gu_name,
                "status":     e.status,
                "details":    e.details,
                "created_at": e.created_at.isoformat(),
            })
        return Response({"total": len(entries), "entries": entries})


class AiAnalyzeView(APIView):
    """POST /api/rgf/ai-analyze/ — re-parse a .docx using Mistral AI for better categorization"""
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        filename = file_obj.name
        if not filename.endswith('.docx'):
            return Response({'error': 'Only .docx files are supported'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            _, full_gu_list = services.get_cached_auth()
            result = services.ai_analyze_document(file_obj.read(), filename, full_gu_list)
            return Response(result)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteRecordsView(APIView):
    """DELETE /api/rgf/records/delete/ — delete specific records from planning.gov.kz"""

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
            # Fall back to all records in DB
            record_ids = list(
                ImportRecord.objects.filter(status='success', record_id__isnull=False)
                .values_list('record_id', flat=True)
            )

        if not record_ids:
            return Response({"message": "No records found to delete", "deleted": [], "failed": []})

        try:
            token = services.get_token()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        result = services.delete_records(record_ids, token)
        _log('delete', status_val='success',
             details={'deleted': result['deleted'], 'failed': result['failed']})
        return Response({
            "total":          len(record_ids),
            "deleted_count":  len(result["deleted"]),
            "failed_count":   len(result["failed"]),
            "deleted":        result["deleted"],
            "failed":         result["failed"],
        })
