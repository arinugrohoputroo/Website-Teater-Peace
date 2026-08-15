from django.contrib import messages
from django.db import transaction
from django.shortcuts import render

from apps.accounts.decorators import module_required
from apps.core.models import log_action
from apps.payments.models import Payment
from apps.ticketing.models import Ticket

from .models import CheckIn


@module_required('checkin')
@transaction.atomic
def checkin_scan(request):
    result = None
    if request.method == 'POST':
        token = request.POST.get('token', '').strip()
        ticket_number = request.POST.get('ticket_number', '').strip()
        ticket = None
        if token:
            ticket = Ticket.objects.select_for_update().filter(qr_token=token).select_related(
                'participant', 'order', 'ticket_type'
            ).first()
        elif ticket_number:
            ticket = Ticket.objects.select_for_update().filter(ticket_number=ticket_number).select_related(
                'participant', 'order', 'ticket_type'
            ).first()

        if not ticket:
            messages.error(request, 'Tiket tidak ditemukan atau tidak valid.')
            return render(request, 'checkin/scan.html', {'result': None})

        if ticket.status == Ticket.Status.CANCELLED:
            messages.error(request, 'Tiket dibatalkan.')
            return render(request, 'checkin/scan.html', {'result': ticket})

        if ticket.status == Ticket.Status.USED or CheckIn.objects.filter(ticket=ticket).exists():
            messages.error(request, 'Tiket sudah digunakan / sudah check-in.')
            return render(request, 'checkin/scan.html', {'result': ticket})

        if ticket.status not in (Ticket.Status.ISSUED, Ticket.Status.PAID):
            messages.error(request, 'Tiket belum diterbitkan.')
            return render(request, 'checkin/scan.html', {'result': ticket})

        if not ticket.order.payments.filter(status=Payment.Status.VERIFIED).exists() and ticket.order.status != 'PAID':
            messages.error(request, 'Pembayaran belum valid.')
            return render(request, 'checkin/scan.html', {'result': ticket})

        CheckIn.objects.create(
            ticket=ticket,
            participant=ticket.participant,
            operator=request.user,
        )
        ticket.status = Ticket.Status.USED
        ticket.save(update_fields=['status'])
        log_action(
            request.user,
            'Check-in',
            'checkin',
            ticket.ticket_number,
            f'Check-in ID Tiket {ticket.ticket_number}',
            metadata={
                'collection': ticket.collection_status,
                'channel': ticket.sales_channel,
            },
            request=request,
        )
        messages.success(request, f'Check-in berhasil. ID Tiket {ticket.ticket_number}')
        result = ticket
    return render(request, 'checkin/scan.html', {'result': result})


@module_required('checkin')
def checkin_history(request):
    entries = CheckIn.objects.select_related('participant', 'ticket', 'operator').order_by('-checked_in_at')
    return render(request, 'checkin/history.html', {'entries': entries})
