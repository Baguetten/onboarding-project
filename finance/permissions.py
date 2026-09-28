from rest_framework import permissions

class IsOwner(permissions.BasePermission):
    #Object-level check: only the owner of an object may access it
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user