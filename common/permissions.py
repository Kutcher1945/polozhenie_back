from rest_framework.permissions import BasePermission


class IsNurse(BasePermission):
    """Allow only nurses to access this endpoint."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "nurse"
    
class IsDoctor(BasePermission):
    """Allow only doctors to access this endpoint."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "doctor"

class IsAdmin(BasePermission):
    """Allow only admins to access this endpoint."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"
