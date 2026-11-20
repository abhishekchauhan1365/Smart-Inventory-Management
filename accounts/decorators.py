from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    """Decorator to allow only Administrators or Superusers."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_admin_user():
            messages.error(request, "Access denied. Administrator privileges are required for this action.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def staff_or_admin_required(view_func):
    """Decorator to allow Pharmacy Staff or Administrators."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_staff_user():
            messages.error(request, "Access denied. Authorized pharmacy credentials required.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
