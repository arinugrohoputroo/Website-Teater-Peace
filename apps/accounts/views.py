from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST

from .models import User, StaffPermission
from .decorators import admin_required, panitia_required
from apps.core.models import log_action


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_panitia:
            return redirect('dashboard:index')
        return redirect('core:home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_panitia:
                messages.error(request, 'Akun Anda tidak memiliki akses ke panel panitia.')
                return render(request, 'accounts/login.html')
            if not user.is_active:
                messages.error(request, 'Akun Anda telah dinonaktifkan.')
                return render(request, 'accounts/login.html')
            login(request, user)
            log_action(user, 'Login', 'accounts', user.username, request=request)
            return redirect('dashboard:index')
        else:
            messages.error(request, 'Username atau password salah.')

    return render(request, 'accounts/login.html')


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        log_action(request.user, 'Logout', 'accounts', request.user.username, request=request)
    logout(request)
    messages.success(request, 'Anda telah logout.')
    return redirect('login')


@login_required
def profile(request):
    return render(request, 'accounts/profile.html')


@admin_required
def staff_list(request):
    staff = User.objects.filter(role__in=['STAFF', 'ADMIN']).prefetch_related('staff_permissions')
    return render(request, 'accounts/staff_list.html', {'staff_list': staff})


@admin_required
def staff_add(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        name = request.POST.get('name', '').strip()
        password = request.POST.get('password', '')
        role = request.POST.get('role', 'STAFF')

        if not username or not email or not name or not password:
            messages.error(request, 'Semua field harus diisi.')
            return render(request, 'accounts/staff_add.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" sudah digunakan.')
            return render(request, 'accounts/staff_add.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, f'Email "{email}" sudah digunakan.')
            return render(request, 'accounts/staff_add.html')

        user = User.objects.create_user(
            email=email,
            password=password,
            username=username,
            name=name,
            role=role,
            is_staff=True,
            is_active=True,
        )
        log_action(request.user, 'Add Staff', 'accounts', email, f'Registered {name} as {role}', request=request)
        messages.success(request, f'{name} telah didaftarkan sebagai {role}.')
        return redirect('accounts:staff_list')

    return render(request, 'accounts/staff_add.html')


@admin_required
def staff_edit(request, pk):
    staff = get_object_or_404(User, pk=pk, role__in=['STAFF', 'ADMIN'])

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        role = request.POST.get('role', staff.role)

        if staff.email == request.user.email and role != 'ADMIN':
            messages.error(request, 'Tidak dapat mengubah role akun sendiri.')
            return redirect('accounts:staff_list')

        staff.name = name or staff.name
        staff.email = email or staff.email
        staff.phone = phone
        if role in ('STAFF', 'ADMIN'):
            staff.role = role
        staff.save(update_fields=['name', 'email', 'phone', 'role'])
        log_action(request.user, 'Edit Staff', 'accounts', staff.username, f'Updated {staff.name}', request=request)
        messages.success(request, f'{staff.name} telah diperbarui.')
        return redirect('accounts:staff_list')

    return render(request, 'accounts/staff_edit.html', {'staff': staff})


@admin_required
def staff_reset_password(request, pk):
    staff = get_object_or_404(User, pk=pk, role__in=['STAFF', 'ADMIN'])
    if request.method == 'POST':
        password = request.POST.get('password', '')
        if len(password) < 8:
            messages.error(request, 'Password minimal 8 karakter.')
            return redirect('accounts:staff_list')
        staff.set_password(password)
        staff.save(update_fields=['password'])
        log_action(request.user, 'Reset Password', 'accounts', staff.username, f'Password reset for {staff.name}', request=request)
        messages.success(request, f'Password {staff.name} telah direset.')
    return redirect('accounts:staff_list')


@admin_required
def staff_permissions(request, pk):
    staff = get_object_or_404(User, pk=pk, role__in=['STAFF', 'ADMIN'])

    if request.method == 'POST':
        with transaction.atomic():
            staff.staff_permissions.all().delete()
            modules = request.POST.getlist('modules')
            for module in modules:
                StaffPermission.objects.create(user=staff, module=module)
        log_action(request.user, 'Update Permission', 'accounts', staff.username, f'Modules: {modules}', request=request)
        messages.success(request, f'Permission {staff.name} telah diperbarui.')
        return redirect('accounts:staff_list')

    all_modules = StaffPermission.Module.choices
    active_modules = set(staff.staff_permissions.values_list('module', flat=True))
    return render(request, 'accounts/staff_permissions.html', {
        'staff': staff,
        'all_modules': all_modules,
        'active_modules': active_modules,
    })


@admin_required
def staff_toggle(request, pk):
    staff = get_object_or_404(User, pk=pk, role__in=['STAFF', 'ADMIN'])
    if staff.pk == request.user.pk:
        messages.error(request, 'Tidak dapat menonaktifkan akun sendiri.')
        return redirect('accounts:staff_list')
    staff.is_active = not staff.is_active
    staff.save(update_fields=['is_active'])
    status = 'diaktifkan' if staff.is_active else 'dinonaktifkan'
    log_action(request.user, 'Toggle Staff', 'accounts', staff.username, f'{staff.name} {status}', request=request)
    messages.success(request, f'{staff.name} telah {status}.')
    return redirect('accounts:staff_list')


@admin_required
def staff_delete(request, pk):
    staff = get_object_or_404(User, pk=pk, role='STAFF')
    if request.method == 'POST':
        name = staff.name
        username = staff.username
        staff.role = 'CUSTOMER'
        staff.is_staff = False
        staff.staff_permissions.all().delete()
        staff.save(update_fields=['role', 'is_staff'])
        log_action(request.user, 'Remove Staff', 'accounts', username, f'{name} removed from staff', request=request)
        messages.success(request, f'{name} telah dihapus dari panitia.')
    return redirect('accounts:staff_list')
