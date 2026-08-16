from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required, module_required
from apps.core.models import log_action
from apps.ticketing.services import (
    get_available_ticket_numbers,
    issue_tickets_for_order,
    parse_ticket_numbers,
)

from .models import Payment, PaymentMethod


@module_required('payment')
def payment_list(request):
    payments = Payment.objects.select_related('order', 'payment_method', 'verified_by').order_by('-created_at')
    status = request.GET.get('status', '')
    if status:
        payments = payments.filter(status=status)
    return render(request, 'payments/list.html', {'payments': payments, 'status': status})


@module_required('payment')
def payment_verify(request, pk):
    payment = get_object_or_404(
        Payment.objects.select_related('order', 'payment_method').prefetch_related(
            'order__order_items__ticket_type',
            'order__tickets',
        ),
        pk=pk,
    )
    if payment.status != Payment.Status.PENDING:
        messages.info(request, 'Pembayaran sudah diproses.')
        return redirect('payments:list')

    existing_tickets = list(payment.order.tickets.order_by('ticket_number'))
    if existing_tickets:
        return render(request, 'payments/verify.html', {
            'payment': payment,
            'needed_qty': len(existing_tickets),
            'order_items': payment.order.order_items.select_related('ticket_type'),
            'existing_tickets': existing_tickets,
            'available_preview': [],
            'available_total': 0,
            'available_has_more': False,
        })

    needed_qty = payment.order.quantity
    available_preview, available_total, available_has_more = get_available_ticket_numbers(limit=150)
    return render(request, 'payments/verify.html', {
        'payment': payment,
        'needed_qty': needed_qty,
        'order_items': payment.order.order_items.select_related('ticket_type'),
        'existing_tickets': [],
        'available_preview': available_preview,
        'available_total': available_total,
        'available_has_more': available_has_more,
    })


@admin_required
def payment_method_list(request):
    methods = PaymentMethod.objects.order_by('name')
    return render(request, 'payments/methods.html', {'methods': methods})


def _save_payment_method(request, method=None):
    name = request.POST.get('name', '').strip()
    ptype = request.POST.get('type', PaymentMethod.Type.BANK)
    account_number = request.POST.get('account_number', '').strip()
    account_name = request.POST.get('account_name', '').strip()
    instructions = request.POST.get('instructions', '').strip()
    active = request.POST.get('active') == 'on'

    if not name:
        messages.error(request, 'Nama metode pembayaran wajib diisi.')
        return False

    if method is None:
        method = PaymentMethod()
    method.name = name
    method.type = ptype if ptype in PaymentMethod.Type.values else PaymentMethod.Type.BANK
    method.account_number = account_number
    method.account_name = account_name
    method.instructions = instructions
    method.active = active
    if request.FILES.get('qr_image'):
        method.qr_image = request.FILES['qr_image']
    method.save()
    return method


@admin_required
def payment_method_add(request):
    if request.method == 'POST':
        method = _save_payment_method(request)
        if method:
            log_action(request.user, 'Add Payment Method', 'payments', method.name, request=request)
            messages.success(request, f'Metode {method.name} ditambahkan.')
            return redirect('payments:methods')
    return render(request, 'payments/method_form.html', {
        'form_title': 'Tambah Metode Pembayaran',
        'method': None,
        'types': PaymentMethod.Type.choices,
    })


@admin_required
def payment_method_edit(request, pk):
    method = get_object_or_404(PaymentMethod, pk=pk)
    if request.method == 'POST':
        saved = _save_payment_method(request, method)
        if saved:
            log_action(request.user, 'Edit Payment Method', 'payments', method.name, request=request)
            messages.success(request, f'Metode {method.name} diperbarui.')
            return redirect('payments:methods')
    return render(request, 'payments/method_form.html', {
        'form_title': 'Edit Metode Pembayaran',
        'method': method,
        'types': PaymentMethod.Type.choices,
    })


@admin_required
@require_POST
def payment_method_toggle(request, pk):
    method = get_object_or_404(PaymentMethod, pk=pk)
    method.active = not method.active
    method.save(update_fields=['active'])
    messages.success(request, f'{method.name} {"diaktifkan" if method.active else "dinonaktifkan"}.')
    return redirect('payments:methods')


@admin_required
@require_POST
def payment_method_delete(request, pk):
    method = get_object_or_404(PaymentMethod, pk=pk)
    if Payment.objects.filter(payment_method=method).exists():
        messages.error(request, 'Metode masih dipakai transaksi. Nonaktifkan saja.')
        return redirect('payments:methods')
    name = method.name
    method.delete()
    log_action(request.user, 'Delete Payment Method', 'payments', name, request=request)
    messages.success(request, f'{name} dihapus.')
    return redirect('payments:methods')


@module_required('payment')
@transaction.atomic
def payment_approve(request, pk):
    payment = get_object_or_404(Payment.objects.select_for_update().select_related('order'), pk=pk)
    if payment.status == Payment.Status.VERIFIED:
        messages.info(request, 'Pembayaran sudah pernah diverifikasi.')
        return redirect('payments:list')

    if request.method != 'POST':
        if payment.status == Payment.Status.PENDING and not payment.order.tickets.exists():
            return redirect('payments:verify', pk=payment.pk)
        return redirect('payments:list')

    ticket_numbers = None
    if not payment.order.tickets.exists():
        raw_numbers = request.POST.get('ticket_numbers', '').strip()
        if not raw_numbers:
            messages.error(request, 'Pilih ID tiket yang akan diterbitkan.')
            return redirect('payments:verify', pk=payment.pk)
        try:
            ticket_numbers = parse_ticket_numbers(raw_numbers)
            needed = payment.order.quantity
            if len(ticket_numbers) != needed:
                messages.error(request, f'Jumlah ID tiket harus {needed}.')
                return redirect('payments:verify', pk=payment.pk)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('payments:verify', pk=payment.pk)

    try:
        payment.status = Payment.Status.VERIFIED
        payment.verified_by = request.user
        payment.verified_at = timezone.now()
        payment.rejection_reason = ''
        payment.save(update_fields=['status', 'verified_by', 'verified_at', 'rejection_reason', 'updated_at'])
        payment.order.status = 'PAID'
        payment.order.save(update_fields=['status', 'updated_at'])
        issued = issue_tickets_for_order(
            payment.order,
            operator=request.user,
            request=request,
            ticket_numbers=ticket_numbers,
        )
    except ValueError as exc:
        transaction.set_rollback(True)
        messages.error(request, str(exc))
        return redirect('payments:verify', pk=payment.pk)

    log_action(
        request.user,
        'Payment Approval',
        'payments',
        payment.pk,
        f'Pembayaran {payment.order.order_number} disetujui',
        metadata={'tickets': [ticket.ticket_number for ticket in issued]},
        request=request,
    )
    ticket_ids = ', '.join(ticket.ticket_number for ticket in issued) or '-'
    messages.success(request, f'Pembayaran disetujui. ID Tiket: {ticket_ids}')
    return redirect('ticketing:order_detail', order_number=payment.order.order_number)


@module_required('payment')
@transaction.atomic
def payment_reject(request, pk):
    if request.method != 'POST':
        return redirect('payments:list')
    payment = get_object_or_404(Payment.objects.select_for_update().select_related('order'), pk=pk)
    reason = request.POST.get('reason', '').strip()
    payment.status = Payment.Status.REJECTED
    payment.verified_by = request.user
    payment.verified_at = timezone.now()
    payment.rejection_reason = reason
    payment.save(update_fields=['status', 'verified_by', 'verified_at', 'rejection_reason', 'updated_at'])
    payment.order.status = 'REJECTED'
    payment.order.save(update_fields=['status', 'updated_at'])
    log_action(
        request.user,
        'Payment Rejection',
        'payments',
        payment.pk,
        f'Pembayaran {payment.order.order_number} ditolak',
        metadata={'reason': reason},
        request=request,
    )
    messages.success(request, 'Pembayaran ditolak.')
    return redirect('payments:list')
