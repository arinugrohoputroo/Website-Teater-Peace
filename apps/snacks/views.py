import json

from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required, module_required
from apps.core.models import log_action

from .models import CommitteeMember, SnackClaim, SnackSession
from .services import committee_qr_data_uri, generate_committee_qr, process_qr_snack_scan, serialize_qr_scan_result


def _snack_stats(session=None):
    total_committee = CommitteeMember.objects.filter(active=True).count()
    active_sessions = SnackSession.objects.filter(active=True).count()
    claims_qs = SnackClaim.objects.filter(committee_member__isnull=False)
    if session:
        claims_qs = claims_qs.filter(session=session)
    claimed = claims_qs.values('committee_member_id').distinct().count()
    return {
        'total_committee': total_committee,
        'active_sessions': active_sessions,
        'claimed_count': claimed,
        'unclaimed_count': max(0, total_committee - claimed),
    }


@module_required('snack')
def session_list(request):
    sessions = SnackSession.objects.annotate(
        claim_count=Count('snackclaim', filter=Q(snackclaim__committee_member__isnull=False)),
    ).order_by('-date', 'start_time')
    stats = _snack_stats()
    recent_claims = SnackClaim.objects.select_related(
        'committee_member', 'session', 'operator',
    ).filter(committee_member__isnull=False).order_by('-claimed_at')[:10]
    return render(request, 'snacks/list.html', {
        'sessions': sessions,
        'stats': stats,
        'recent_claims': recent_claims,
    })


@admin_required
def scanner(request):
    sessions = SnackSession.objects.filter(active=True).order_by('date', 'start_time')
    return render(request, 'snacks/scanner.html', {'sessions': sessions})


@admin_required
@require_POST
def scanner_process(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({
            'success': False,
            'status': 'error',
            'message': 'Payload tidak valid.',
        }, status=400)

    session_id = payload.get('session_id')
    qr_token = payload.get('qr_token', '')
    session = SnackSession.objects.filter(pk=session_id).first()
    if not session:
        return JsonResponse({
            'success': False,
            'status': 'invalid_session',
            'message': 'Sesi snack tidak ditemukan.',
        }, status=400)

    result = process_qr_snack_scan(
        qr_token=qr_token,
        session=session,
        operator=request.user,
    )
    return JsonResponse(serialize_qr_scan_result(result))


@admin_required
def history(request):
    claims = SnackClaim.objects.select_related(
        'committee_member', 'session', 'operator',
    ).filter(committee_member__isnull=False)

    session_id = request.GET.get('session')
    if session_id:
        claims = claims.filter(session_id=session_id)
    date = request.GET.get('date')
    if date:
        claims = claims.filter(claimed_at__date=date)
    q = request.GET.get('q', '').strip()
    if q:
        claims = claims.filter(
            Q(committee_member__name__icontains=q) |
            Q(committee_member__member_code__icontains=q)
        )

    sessions = SnackSession.objects.order_by('-date', 'start_time')
    return render(request, 'snacks/history.html', {
        'claims': claims[:500],
        'sessions': sessions,
        'filters': {'session': session_id or '', 'date': date or '', 'q': q},
    })


@admin_required
def committee_list(request):
    members = CommitteeMember.objects.all()
    return render(request, 'snacks/committee_list.html', {'members': members})


@admin_required
def committee_add(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Nama panitia wajib diisi.')
        elif CommitteeMember.objects.filter(name__iexact=name).exists():
            messages.error(request, 'Nama panitia sudah terdaftar.')
        else:
            member = CommitteeMember(name=name, active=True)
            member.save()
            log_action(request.user, 'Add Committee', 'snacks', member.member_code, member.name, request=request)
            messages.success(request, f'Panitia {member.name} ditambahkan ({member.member_code}).')
            return redirect('snacks:committee_detail', pk=member.pk)
    return render(request, 'snacks/committee_form.html', {
        'form_title': 'Tambah Panitia',
        'member': None,
    })


@admin_required
def committee_edit(request, pk):
    member = get_object_or_404(CommitteeMember, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        active = request.POST.get('active') == 'on'
        if not name:
            messages.error(request, 'Nama panitia wajib diisi.')
        elif CommitteeMember.objects.exclude(pk=member.pk).filter(name__iexact=name).exists():
            messages.error(request, 'Nama panitia sudah digunakan.')
        else:
            member.name = name
            member.active = active
            member.save()
            log_action(request.user, 'Edit Committee', 'snacks', member.member_code, member.name, request=request)
            messages.success(request, f'Panitia {member.name} diperbarui.')
            return redirect('snacks:committee_detail', pk=member.pk)
    return render(request, 'snacks/committee_form.html', {
        'form_title': 'Edit Panitia',
        'member': member,
    })


@admin_required
@require_POST
def committee_toggle(request, pk):
    member = get_object_or_404(CommitteeMember, pk=pk)
    member.active = not member.active
    member.save(update_fields=['active', 'updated_at'])
    messages.success(request, f'{member.name} {"diaktifkan" if member.active else "dinonaktifkan"}.')
    return redirect('snacks:committee_list')


@admin_required
@require_POST
def committee_delete(request, pk):
    member = get_object_or_404(CommitteeMember, pk=pk)
    name = member.name
    code = member.member_code
    claim_count = SnackClaim.objects.filter(committee_member=member).count()
    SnackClaim.objects.filter(committee_member=member).delete()
    member.delete()
    log_action(
        request.user,
        'Delete Committee',
        'snacks',
        code,
        f'{name} dihapus ({claim_count} claim)',
        request=request,
    )
    messages.success(request, f'{name} dihapus.')
    return redirect('snacks:committee_list')


@admin_required
@require_POST
def claim_delete(request, pk):
    claim = get_object_or_404(
        SnackClaim.objects.select_related('committee_member', 'session'),
        pk=pk,
    )
    member_name = claim.committee_member.name if claim.committee_member else '-'
    session_name = claim.session.name
    member_pk = claim.committee_member_id
    claim.delete()
    log_action(
        request.user,
        'Delete Snack Claim',
        'snacks',
        session_name,
        f'Hapus claim {member_name} · {session_name}',
        request=request,
    )
    messages.success(request, f'Claim {member_name} dihapus.')
    next_url = request.POST.get('next', '')
    if next_url:
        return redirect(next_url)
    if member_pk:
        return redirect('snacks:committee_detail', pk=member_pk)
    return redirect('snacks:history')


@admin_required
def committee_qr_list(request):
    members = CommitteeMember.objects.all()
    cards = [
        {
            'member': m,
            'qr_data_uri': committee_qr_data_uri(m, box_size=8, border=4),
        }
        for m in members
    ]
    return render(request, 'snacks/committee_qr_list.html', {'cards': cards})


@admin_required
def committee_qr_print(request):
    members = CommitteeMember.objects.all()
    cards = [
        {
            'member': m,
            'qr_data_uri': committee_qr_data_uri(m, box_size=12, border=4),
        }
        for m in members
    ]
    return render(request, 'snacks/committee_qr_print.html', {'cards': cards})


@admin_required
def committee_detail(request, pk):
    member = get_object_or_404(CommitteeMember, pk=pk)
    sessions = SnackSession.objects.order_by('date', 'start_time')
    claims = {
        c.session_id: c
        for c in SnackClaim.objects.filter(committee_member=member).select_related('session', 'operator')
    }
    session_rows = []
    for session in sessions:
        claim = claims.get(session.pk)
        session_rows.append({'session': session, 'claim': claim})
    return render(request, 'snacks/committee_detail.html', {
        'member': member,
        'qr_data_uri': committee_qr_data_uri(member, box_size=10, border=4),
        'session_rows': session_rows,
    })


@admin_required
@require_POST
def committee_regenerate_qr(request, pk):
    member = get_object_or_404(CommitteeMember, pk=pk)
    old_token = member.qr_token
    member.regenerate_qr_token()
    messages.success(request, f'QR {member.member_code} digenerate ulang. Token lama tidak berlaku.')
    log_action(
        request.user,
        'QR_REGENERATE',
        'snacks',
        member.member_code,
        f'Regenerate QR {member.name}',
        metadata={'old_token': old_token, 'new_token': member.qr_token},
        request=request,
    )
    return redirect('snacks:committee_detail', pk=member.pk)


@admin_required
def committee_qr_download(request, pk):
    member = get_object_or_404(CommitteeMember, pk=pk)
    img = generate_committee_qr(member, box_size=14, border=4)
    response = HttpResponse(content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="{member.member_code}-qr.png"'
    img.save(response, format='PNG')
    return response


@module_required('snack')
def scan_claim(request):
    if request.user.is_admin:
        return redirect('snacks:scanner')
    messages.info(request, 'Scanner QR hanya untuk Admin.')
    return redirect('snacks:list')


def _save_snack_session(request, session=None):
    name = request.POST.get('name', '').strip()
    date = request.POST.get('date', '').strip()
    start_time = request.POST.get('start_time', '').strip()
    end_time = request.POST.get('end_time', '').strip()
    active = request.POST.get('active') == 'on'

    if not name or not date or not start_time or not end_time:
        messages.error(request, 'Semua field wajib diisi.')
        return False

    if session is None:
        session = SnackSession()
    session.name = name
    session.date = date
    session.start_time = start_time
    session.end_time = end_time
    session.active = active
    session.save()
    return session


@admin_required
def session_add(request):
    if request.method == 'POST':
        saved = _save_snack_session(request)
        if saved:
            log_action(request.user, 'Add Snack Session', 'snacks', saved.name, request=request)
            messages.success(request, f'Sesi {saved.name} ditambahkan.')
            return redirect('snacks:list')
    return render(request, 'snacks/session_form.html', {
        'form_title': 'Tambah Sesi Snack',
        'session_obj': None,
    })


@admin_required
def session_edit(request, pk):
    session_obj = get_object_or_404(SnackSession, pk=pk)
    if request.method == 'POST':
        saved = _save_snack_session(request, session_obj)
        if saved:
            log_action(request.user, 'Edit Snack Session', 'snacks', saved.name, request=request)
            messages.success(request, f'Sesi {saved.name} diperbarui.')
            return redirect('snacks:list')
    return render(request, 'snacks/session_form.html', {
        'form_title': 'Edit Sesi Snack',
        'session_obj': session_obj,
    })


@admin_required
@require_POST
def session_toggle(request, pk):
    session_obj = get_object_or_404(SnackSession, pk=pk)
    session_obj.active = not session_obj.active
    session_obj.save(update_fields=['active'])
    messages.success(request, f'{session_obj.name} {"diaktifkan" if session_obj.active else "dinonaktifkan"}.')
    return redirect('snacks:list')


@admin_required
@require_POST
def session_delete(request, pk):
    session_obj = get_object_or_404(SnackSession, pk=pk)
    name = session_obj.name
    claim_count = SnackClaim.objects.filter(session=session_obj).count()
    SnackClaim.objects.filter(session=session_obj).delete()
    session_obj.delete()
    log_action(
        request.user,
        'Delete Snack Session',
        'snacks',
        name,
        f'{name} dihapus ({claim_count} claim)',
        request=request,
    )
    messages.success(request, f'{name} dihapus.')
    return redirect('snacks:list')
