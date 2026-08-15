from functools import wraps
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from django.views.decorators.cache import never_cache


def panitia_required(view_func):
    @never_cache
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_panitia:
            return HttpResponseForbidden('Akses ditolak')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    @never_cache
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_admin:
            return HttpResponseForbidden('Akses ditolak')
        return view_func(request, *args, **kwargs)
    return wrapper


def module_required(module_name):
    def decorator(view_func):
        @never_cache
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.is_admin:
                return view_func(request, *args, **kwargs)
            if not request.user.is_panitia:
                return HttpResponseForbidden('Akses ditolak')
            if not request.user.staff_permissions.filter(module=module_name).exists():
                return HttpResponseForbidden('Anda tidak memiliki akses ke modul ini')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
