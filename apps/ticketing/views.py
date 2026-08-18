from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.decorators import admin_required, module_required
from apps.core.models import log_action
from apps.payments.models import PaymentMethod

from .models import Order, ShowScript, Ticket, TicketType
from .services import (
    create_offline_order,
    delete_order,
    get_available_ticket_numbers,
    mark_ticket_collected,
    normalize_ticket_number,
    parse_ticket_numbers,
    ticket_types_with_stats,
)


@module_required('ticketing')
def order_list(request):
    orders = Order.objects.prefetch_related('order_items', 'tickets', 'payments').order_by('-created_at')
    channel = request.GET.get('channel', '')
    if channel in ('ONLINE', 'OFFLINE'):
        orders = orders.filter(channel=channel)
    order_rows = [{'order': order, 'can_delete': True} for order in orders]
    return render(request, 'ticketing/order_list.html', {
        'order_rows': order_rows,
        'channel': channel,
    })


@module_required('ticketing')
def order_detail(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related('tickets__ticket_type', 'tickets__participant', 'order_items__ticket_type', 'payments'),
        order_number=order_number,
    )
    tickets = order.tickets.select_related('ticket_type', 'participant').order_by('ticket_number')
    return render(request, 'ticketing/order_detail.html', {
        'order': order,
        'tickets': tickets,
        'payment': order.payments.order_by('-created_at').first(),
        'can_delete': True,
    })


@admin_required
@require_POST
def order_delete(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    try:
        deleted = delete_order(order, request.user, request=request)
        messages.success(request, f'Order {deleted} dihapus.')
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('ticketing:order_detail', order_number=order_number)
    return redirect('ticketing:list')


@module_required('ticketing')
def ticket_list(request):
    tickets = Ticket.objects.select_related(
        'order', 'participant', 'ticket_type', 'collected_by'
    ).order_by('ticket_number')

    q = request.GET.get('q', '').strip()
    channel = request.GET.get('channel', '')
    collection = request.GET.get('collection', '')
    season = request.GET.get('season', '')
    payment = request.GET.get('payment', '')

    if q:
        tickets = tickets.filter(
            Q(ticket_number__icontains=q)
            | Q(order__order_number__icontains=q)
            | Q(participant__name__icontains=q)
            | Q(order__buyer_name__icontains=q)
            | Q(order__buyer_phone__icontains=q)
            | Q(participant__phone__icontains=q)
        )
    if channel in ('ONLINE', 'OFFLINE'):
        tickets = tickets.filter(sales_channel=channel)
    if collection in ('NOT_COLLECTED', 'COLLECTED'):
        tickets = tickets.filter(collection_status=collection)
    if season:
        tickets = tickets.filter(ticket_type_id=season)
    if payment == 'VERIFIED':
        tickets = tickets.filter(order__status=Order.Status.PAID)
    elif payment == 'PENDING':
        tickets = tickets.exclude(order__status=Order.Status.PAID)

    return render(request, 'ticketing/ticket_list.html', {
        'tickets': tickets,
        'ticket_types': TicketType.objects.filter(active=True),
        'q': q,
        'channel': channel,
        'collection': collection,
        'season': season,
        'payment': payment,
    })


@module_required('ticketing')
def ticket_detail(request, ticket_number):
    ticket = get_object_or_404(
        Ticket.objects.select_related('order', 'participant', 'ticket_type', 'collected_by'),
        ticket_number=ticket_number,
    )
    return render(request, 'ticketing/ticket_detail.html', {
        'ticket': ticket,
    })


@module_required('ticketing')
def ticket_collection(request):
    result = None
    results = []
    q = request.GET.get('q', '').strip() or request.POST.get('q', '').strip()
    selected = request.GET.get('ticket', '').strip()

    if request.method == 'POST' and request.POST.get('action') == 'collect':
        ticket = None
        ticket_pk = _safe_pk(request.POST.get('ticket_id'))
        if ticket_pk:
            ticket = Ticket.objects.filter(pk=ticket_pk).first()
        if ticket is None:
            ticket_no = request.POST.get('ticket_number', '').strip() or q
            if ticket_no:
                try:
                    ticket_no = normalize_ticket_number(ticket_no)
                    ticket = Ticket.objects.filter(ticket_number=ticket_no).first()
                except ValueError:
                    pass
        if ticket is None:
            messages.error(request, 'Tiket tidak ditemukan.')
            return redirect(f"{reverse('ticketing:collection')}?q={q}" if q else 'ticketing:collection')

        try:
            ticket = mark_ticket_collected(ticket, request.user, request=request)
            messages.success(request, f'Tiket fisik {ticket.ticket_number} berhasil diserahkan.')
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect(f"{reverse('ticketing:collection')}?q={ticket.ticket_number}")

    search_q = selected or q
    if search_q:
        filters = (
            Q(order__order_number__icontains=search_q)
            | Q(order__buyer_phone__icontains=search_q)
            | Q(order__buyer_name__icontains=search_q)
            | Q(participant__name__icontains=search_q)
            | Q(qr_token__iexact=search_q)
        )
        try:
            normalized = normalize_ticket_number(search_q)
            filters |= Q(ticket_number=normalized)
        except ValueError:
            filters |= Q(ticket_number__icontains=search_q)

        matched = Ticket.objects.select_related(
            'order', 'participant', 'ticket_type', 'collected_by'
        ).filter(filters).order_by('ticket_number')
        total = matched.count()
        results = list(matched[:50])
        if selected:
            try:
                selected_no = normalize_ticket_number(selected)
            except ValueError:
                selected_no = None
            if selected_no:
                result = next((t for t in results if t.ticket_number == selected_no), None)
                if result is None:
                    try:
                        result = Ticket.objects.select_related(
                            'order', 'participant', 'ticket_type', 'collected_by'
                        ).get(ticket_number=selected_no)
                    except Ticket.DoesNotExist:
                        result = None
        elif total == 1:
            result = results[0]

    return render(request, 'ticketing/ticket_collection.html', {
        'q': q or selected,
        'result': result,
        'results': results if not result else [],
    })


def _safe_pk(value):
    raw = str(value or '').strip()
    if not raw.isdigit():
        return None
    return int(raw)


@module_required('ticketing')
def offline_sale(request):
    from django.db import IntegrityError

    ticket_types = TicketType.objects.filter(active=True).order_by('name')
    payment_methods = PaymentMethod.objects.filter(active=True).order_by('name')
    available_preview, available_total, available_has_more = get_available_ticket_numbers(limit=150)

    if request.method == 'POST':
        buyer_name = request.POST.get('buyer_name', '').strip()
        buyer_email = request.POST.get('buyer_email', '').strip()
        buyer_phone = request.POST.get('buyer_phone', '').strip()
        ticket_type = TicketType.objects.filter(pk=_safe_pk(request.POST.get('ticket_type'))).first()
        payment_method = PaymentMethod.objects.filter(pk=_safe_pk(request.POST.get('payment_method'))).first()
        ticket_numbers_raw = request.POST.get('ticket_numbers', '').strip()
        is_paid = request.POST.get('payment_status') == 'PAID'
        collect_now = request.POST.get('collect_now') == 'YES'

        if not buyer_name or not buyer_phone or not ticket_type:
            messages.error(request, 'Lengkapi nama, WhatsApp, dan season.')
        elif not ticket_numbers_raw:
            messages.error(request, 'Masukkan ID tiket yang dijual.')
        elif not payment_method:
            messages.error(request, 'Pilih metode pembayaran (Tunai / Cashless / lainnya).')
        else:
            try:
                parsed_numbers = parse_ticket_numbers(ticket_numbers_raw)
                order = create_offline_order(
                    buyer_name=buyer_name,
                    buyer_email=buyer_email,
                    buyer_phone=buyer_phone,
                    ticket_type=ticket_type,
                    quantity=len(parsed_numbers),
                    ticket_numbers=parsed_numbers,
                    payment_method=payment_method,
                    is_paid=is_paid,
                    collect_now=collect_now,
                    operator=request.user,
                    request=request,
                )
                ticket_ids = ', '.join(order.tickets.values_list('ticket_number', flat=True))
                messages.success(
                    request,
                    f'Order offline {order.order_number} berhasil. ID Tiket: {ticket_ids or "-"}',
                )
                return redirect('ticketing:order_detail', order_number=order.order_number)
            except (ValueError, IntegrityError) as exc:
                messages.error(request, str(exc))
            except Exception as exc:
                messages.error(request, f'Gagal menyimpan penjualan: {exc}')

    return render(request, 'ticketing/offline_sale.html', {
        'ticket_types': ticket_types,
        'payment_methods': payment_methods,
        'available_preview': available_preview,
        'available_total': available_total,
        'available_has_more': available_has_more,
    })


@module_required('ticketing')
@require_GET
def available_ticket_ids_api(request):
    try:
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 200))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Parameter tidak valid.'}, status=400)
    search = request.GET.get('q', '').strip()
    ids, total, has_more = get_available_ticket_numbers(
        limit=limit, offset=offset, search=search,
    )
    return JsonResponse({
        'ids': ids,
        'offset': offset,
        'limit': limit,
        'total': total,
        'has_more': has_more,
        'search': search,
    })


@admin_required
def ticket_type_list(request):
    types = ticket_types_with_stats()
    return render(request, 'ticketing/ticket_type_list.html', {'ticket_types': types})


def _save_ticket_type(request, ticket_type=None):
    name = request.POST.get('name', '').strip()
    show_time = request.POST.get('show_time', '').strip()
    price = request.POST.get('price', '').strip()
    bundle_price = request.POST.get('bundle_price', '').strip()
    quota = request.POST.get('quota', '').strip()
    description = request.POST.get('description', '').strip()
    active = request.POST.get('active') == 'on'
    naskah_ids = request.POST.getlist('naskah_ids')

    if not name or not price or not bundle_price or not quota:
        messages.error(request, 'Nama, harga, bundling, dan kuota wajib diisi.')
        return False
    try:
        price_val = int(price)
        bundle_val = int(bundle_price)
        quota_val = int(quota)
    except ValueError:
        messages.error(request, 'Harga dan kuota harus angka.')
        return False

    if ticket_type is not None:
        sold = Ticket.objects.filter(ticket_type=ticket_type).exclude(status=Ticket.Status.CANCELLED).count()
        if quota_val < sold:
            messages.error(request, f'Kuota tidak boleh kurang dari jumlah terjual ({sold}).')
            return False

    if ticket_type is None:
        ticket_type = TicketType()
    ticket_type.name = name
    ticket_type.show_time = show_time
    ticket_type.price = price_val
    ticket_type.bundle_price = bundle_val
    ticket_type.quota = quota_val
    ticket_type.description = description
    ticket_type.active = active
    ticket_type.save()

    if naskah_ids:
        ticket_type.naskah_list.set(ShowScript.objects.filter(id__in=naskah_ids))
    else:
        ticket_type.naskah_list.clear()

    return ticket_type


@admin_required
def ticket_type_add(request):
    if request.method == 'POST':
        saved = _save_ticket_type(request)
        if saved:
            log_action(request.user, 'Add Ticket Type', 'ticketing', saved.name, request=request)
            messages.success(request, f'Jenis tiket {saved.name} ditambahkan.')
            return redirect('ticketing:ticket_types')
    return render(request, 'ticketing/ticket_type_form.html', {
        'form_title': 'Tambah Jenis Tiket',
        'ticket_type': None,
        'all_naskah': ShowScript.objects.all(),
        'selected_naskah_ids': [],
    })


@admin_required
def ticket_type_edit(request, pk):
    ticket_type = get_object_or_404(TicketType, pk=pk)
    if request.method == 'POST':
        saved = _save_ticket_type(request, ticket_type)
        if saved:
            log_action(request.user, 'Edit Ticket Type', 'ticketing', saved.name, request=request)
            messages.success(request, f'Jenis tiket {saved.name} diperbarui.')
            return redirect('ticketing:ticket_types')
    selected_ids = list(ticket_type.naskah_list.values_list('id', flat=True))
    return render(request, 'ticketing/ticket_type_form.html', {
        'form_title': 'Edit Jenis Tiket',
        'ticket_type': ticket_type,
        'all_naskah': ShowScript.objects.all(),
        'selected_naskah_ids': selected_ids,
    })


@admin_required
@require_POST
def ticket_type_toggle(request, pk):
    ticket_type = get_object_or_404(TicketType, pk=pk)
    ticket_type.active = not ticket_type.active
    ticket_type.save(update_fields=['active'])
    messages.success(request, f'{ticket_type.name} {"diaktifkan" if ticket_type.active else "dinonaktifkan"}.')
    return redirect('ticketing:ticket_types')


@admin_required
@require_POST
def ticket_type_delete(request, pk):
    ticket_type = get_object_or_404(TicketType, pk=pk)
    if Ticket.objects.filter(ticket_type=ticket_type).exists():
        messages.error(request, 'Jenis tiket sudah dipakai. Nonaktifkan saja.')
        return redirect('ticketing:ticket_types')
    name = ticket_type.name
    ticket_type.delete()
    log_action(request.user, 'Delete Ticket Type', 'ticketing', name, request=request)
    messages.success(request, f'{name} dihapus.')
    return redirect('ticketing:ticket_types')


# ==========================================
# Naskah Pertunjukan Admin CRUD
# ==========================================

@admin_required
def naskah_list(request):
    naskah = ShowScript.objects.all()
    return render(request, 'ticketing/naskah_list.html', {'naskah_list': naskah})


def _save_naskah(request, naskah=None):
    title = request.POST.get('title', '').strip()
    synopsis = request.POST.get('synopsis', '').strip()
    cast = request.POST.get('cast', '').strip()
    director = request.POST.get('director', '').strip() or 'R. Pujiono'
    production_by = request.POST.get('production_by', '').strip() or 'Teater Peace & Peace Forum'
    order_val = request.POST.get('order', '0').strip()

    if not title:
        messages.error(request, 'Judul Naskah wajib diisi.')
        return False

    try:
        order_num = int(order_val)
    except ValueError:
        order_num = 0

    if naskah is None:
        naskah = ShowScript()

    naskah.title = title
    naskah.synopsis = synopsis
    naskah.cast = cast
    naskah.director = director
    naskah.production_by = production_by
    naskah.order = order_num

    if request.FILES.get('poster'):
        naskah.poster = request.FILES['poster']

    naskah.save()
    return naskah


@admin_required
def naskah_add(request):
    if request.method == 'POST':
        saved = _save_naskah(request)
        if saved:
            log_action(request.user, 'Add Naskah', 'ticketing', saved.title, request=request)
            messages.success(request, f'Naskah "{saved.title}" berhasil ditambahkan.')
            return redirect('ticketing:naskah_list')
    return render(request, 'ticketing/naskah_form.html', {
        'form_title': 'Tambah Naskah Pertunjukan',
        'naskah': None,
    })


@admin_required
def naskah_edit(request, pk):
    naskah = get_object_or_404(ShowScript, pk=pk)
    if request.method == 'POST':
        saved = _save_naskah(request, naskah)
        if saved:
            log_action(request.user, 'Edit Naskah', 'ticketing', saved.title, request=request)
            messages.success(request, f'Naskah "{saved.title}" berhasil diperbarui.')
            return redirect('ticketing:naskah_list')
    return render(request, 'ticketing/naskah_form.html', {
        'form_title': 'Edit Naskah Pertunjukan',
        'naskah': naskah,
    })


@admin_required
@require_POST
def naskah_delete(request, pk):
    naskah = get_object_or_404(ShowScript, pk=pk)
    title = naskah.title
    naskah.delete()
    log_action(request.user, 'Delete Naskah', 'ticketing', title, request=request)
    messages.success(request, f'Naskah "{title}" telah dihapus.')
    return redirect('ticketing:naskah_list')
