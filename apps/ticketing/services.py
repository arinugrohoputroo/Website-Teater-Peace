from django.db import transaction
from django.utils import timezone

from apps.core.models import log_action
from apps.participants.models import Participant

from django.db.models import Count, F, Q, Value, Case, When, IntegerField

from .models import Order, OrderItem, Ticket, TicketType

def get_max_tickets():
    from apps.core.models import EventConfig
    try:
        val = EventConfig.get('max_tickets', '1000')
        return int(val)
    except (ValueError, TypeError):
        return 1000



def ticket_types_with_stats(*, active_only=False):
    qs = TicketType.objects.annotate(
        sold=Count('tickets', filter=~Q(tickets__status=Ticket.Status.CANCELLED)),
    ).annotate(
        remaining_qty=Case(
            When(quota__gte=F('sold'), then=F('quota') - F('sold')),
            default=Value(0),
            output_field=IntegerField(),
        ),
    )
    if active_only:
        qs = qs.filter(active=True)
    return qs.order_by('name')


def get_quota_summary():
    types = list(ticket_types_with_stats())
    total_quota = sum(t.quota for t in types)
    total_sold = sum(t.sold for t in types)
    return {
        'types': types,
        'total_quota': total_quota,
        'total_sold': total_sold,
        'total_remaining': max(0, total_quota - total_sold),
    }


def normalize_ticket_number(value):
    raw = str(value or '').strip()
    max_tickets = get_max_tickets()
    if not raw:
        raise ValueError('ID tiket kosong.')
    if not raw.isdigit():
        raise ValueError(f'ID tiket tidak valid: {value}')
    number = int(raw)
    if number < 1 or number > max_tickets:
        raise ValueError(f'ID tiket harus antara 0001 dan {max_tickets:04d}.')
    return f'{number:04d}'


def parse_ticket_numbers(raw):
    if not raw:
        return []
    parts = []
    for chunk in str(raw).replace('\n', ',').replace(';', ',').split(','):
        chunk = chunk.strip()
        if chunk:
            parts.append(normalize_ticket_number(chunk))
    if len(parts) != len(set(parts)):
        raise ValueError('ID tiket tidak boleh duplikat.')
    return parts


def get_available_ticket_numbers(limit=200):
    max_tickets = get_max_tickets()
    used = set(
        Ticket.objects.exclude(status=Ticket.Status.CANCELLED).values_list('ticket_number', flat=True)
    )
    available = [f'{n:04d}' for n in range(1, max_tickets + 1) if f'{n:04d}' not in used]
    return available[:limit], len(available)


def validate_ticket_numbers(ticket_numbers):
    if not ticket_numbers:
        raise ValueError('Masukkan minimal satu ID tiket.')
    used = set(
        Ticket.objects.exclude(status=Ticket.Status.CANCELLED).values_list('ticket_number', flat=True)
    )
    for number in ticket_numbers:
        if number in used:
            raise ValueError(f'ID tiket {number} sudah terpakai.')
    return ticket_numbers


def get_next_ticket_number():
    last_ticket = Ticket.objects.select_for_update().order_by('-ticket_number').first()
    if not last_ticket:
        return 1
    return int(last_ticket.ticket_number) + 1


def validate_ticket_capacity(quantity):
    max_tickets = get_max_tickets()
    issued = Ticket.objects.exclude(status=Ticket.Status.CANCELLED).count()
    remaining = max_tickets - issued
    if quantity > remaining:
        raise ValueError('Tiket sudah habis atau jumlah melebihi stok tersisa.')
    return remaining


@transaction.atomic
def issue_tickets_for_order(order, operator=None, participant_payloads=None, request=None, auto_collect=None, ticket_numbers=None):
    if order.tickets.exists():
        return list(order.tickets.all())

    payment = order.payments.order_by('-created_at').first()
    if payment and payment.status != 'VERIFIED' and order.status != Order.Status.PAID:
        raise ValueError('Pembayaran belum terverifikasi.')

    items = list(order.order_items.select_related('ticket_type').all())
    if not items:
        raise ValueError('Order belum memiliki item tiket.')

    total_qty = sum(item.quantity for item in items)
    validate_ticket_capacity(total_qty)

    if ticket_numbers is not None:
        ticket_numbers = validate_ticket_numbers(parse_ticket_numbers(ticket_numbers) if isinstance(ticket_numbers, str) else list(ticket_numbers))
        if len(ticket_numbers) != total_qty:
            raise ValueError('Jumlah ID tiket harus sama dengan jumlah tiket di order.')
        numbers_queue = list(ticket_numbers)
    else:
        numbers_queue = []
        max_tickets = get_max_tickets()
        next_number = get_next_ticket_number()
        for _ in range(total_qty):
            if next_number > max_tickets:
                raise ValueError(f'Nomor tiket melebihi batas maksimum {max_tickets}.')
            numbers_queue.append(f'{next_number:04d}')
            next_number += 1

    created = []
    participant_payloads = participant_payloads or []
    payload_index = 0

    if auto_collect is None:
        auto_collect = order.channel == Order.Channel.OFFLINE

    for item in items:
        ticket_type = item.ticket_type
        sold_for_type = Ticket.objects.filter(
            ticket_type=ticket_type,
        ).exclude(status=Ticket.Status.CANCELLED).count()
        if sold_for_type + item.quantity > ticket_type.quota:
            raise ValueError(f'Kuota {ticket_type.name} tidak mencukupi.')

        for _ in range(item.quantity):
            ticket_num = numbers_queue.pop(0)
            payload = participant_payloads[payload_index] if payload_index < len(participant_payloads) else {}
            payload_index += 1
            participant = Participant.objects.create(
                name=payload.get('name') or order.buyer_name,
                phone=payload.get('phone') or order.buyer_phone,
                email=payload.get('email') or order.buyer_email,
                institution=payload.get('institution', ''),
                category=payload.get('category') or Participant.Category.UMUM,
            )
            ticket = Ticket.objects.create(
                ticket_number=ticket_num,
                order=order,
                order_item=item,
                participant=participant,
                ticket_type=ticket_type,
                sales_channel=order.channel,
                status=Ticket.Status.ISSUED,
                collection_status=(
                    Ticket.CollectionStatus.COLLECTED
                    if auto_collect
                    else Ticket.CollectionStatus.NOT_COLLECTED
                ),
                collected_at=timezone.now() if auto_collect else None,
                collected_by=operator if auto_collect else None,
            )
            created.append(ticket)

    order.status = Order.Status.PAID
    order.save(update_fields=['status', 'updated_at'])
    log_action(
        operator,
        'Ticket Generation',
        'ticketing',
        order.order_number,
        f'{len(created)} tiket diterbitkan untuk {order.order_number}',
        metadata={
            'tickets': [ticket.ticket_number for ticket in created],
            'channel': order.channel,
        },
        request=request,
    )
    return created


@transaction.atomic
def create_public_order(*, buyer_name, buyer_email, buyer_phone, items, payment_method=None, notes=''):
    if not items:
        raise ValueError('Pilih minimal satu tiket.')
    total_requested = sum(int(item['quantity']) for item in items if int(item['quantity']) > 0)
    validate_ticket_capacity(total_requested)

    order = Order.objects.create(
        buyer_name=buyer_name,
        buyer_email=buyer_email,
        buyer_phone=buyer_phone,
        channel=Order.Channel.ONLINE,
        total_amount=0,
        status=Order.Status.WAITING_PAYMENT,
        notes=notes,
    )

    total = 0
    created_items = []
    max_tickets = get_max_tickets()
    remaining_global = max_tickets - Ticket.objects.exclude(status=Ticket.Status.CANCELLED).count()
    for item in items:
        ticket_type = TicketType.objects.select_for_update().get(pk=item['ticket_type'].pk)
        quantity = int(item['quantity'])
        if quantity <= 0:
            continue
        if quantity > remaining_global:
            raise ValueError('Tiket sudah habis atau jumlah melebihi stok tersisa.')
        if quantity > ticket_type.quota - Ticket.objects.filter(ticket_type=ticket_type).exclude(status=Ticket.Status.CANCELLED).count():
            raise ValueError(f'Kuota {ticket_type.name} tidak mencukupi.')
        subtotal = ticket_type.calculate_subtotal(quantity)
        created_items.append(OrderItem.objects.create(
            order=order,
            ticket_type=ticket_type,
            quantity=quantity,
            price=ticket_type.price,
            subtotal=subtotal,
        ))
        total += subtotal
        remaining_global -= quantity

    if not created_items:
        raise ValueError('Pilih minimal satu tiket.')

    order.total_amount = total
    order.save(update_fields=['total_amount', 'updated_at'])

    if payment_method:
        from apps.payments.models import Payment
        Payment.objects.create(
            order=order,
            payment_method=payment_method,
            amount=total,
            status='PENDING',
        )
    log_action(
        None,
        'Create Order',
        'ticketing',
        order.order_number,
        f'Order ONLINE dibuat untuk {buyer_name}',
        metadata={'channel': order.channel, 'total_amount': str(total)},
    )
    return order


@transaction.atomic
def create_offline_order(*, buyer_name, buyer_email, buyer_phone, ticket_type, quantity, payment_method=None, is_paid=False, collect_now=True, operator=None, request=None, ticket_numbers=None):
    if ticket_numbers:
        parsed_numbers = parse_ticket_numbers(ticket_numbers) if isinstance(ticket_numbers, str) else validate_ticket_numbers(list(ticket_numbers))
        quantity = len(parsed_numbers)
    elif quantity <= 0:
        raise ValueError('Jumlah tiket harus lebih dari 0.')
    else:
        parsed_numbers = None

    validate_ticket_capacity(quantity)
    order = Order(
        buyer_name=buyer_name,
        buyer_email=buyer_email,
        buyer_phone=buyer_phone,
        customer=operator,
        channel=Order.Channel.OFFLINE,
        total_amount=0,
        status=Order.Status.PAID if is_paid else Order.Status.WAITING_PAYMENT,
    )
    order.save()
    subtotal = ticket_type.calculate_subtotal(quantity)
    OrderItem.objects.create(
        order=order,
        ticket_type=ticket_type,
        quantity=quantity,
        price=ticket_type.price,
        subtotal=subtotal,
    )
    order.total_amount = subtotal
    order.save(update_fields=['total_amount', 'updated_at'])

    from apps.payments.models import Payment

    payment = None
    if payment_method:
        payment = Payment.objects.create(
            order=order,
            payment_method=payment_method,
            amount=subtotal,
            status=Payment.Status.VERIFIED if is_paid else Payment.Status.PENDING,
            verified_by=operator if is_paid else None,
            verified_at=timezone.now() if is_paid else None,
        )

    if is_paid:
        issue_tickets_for_order(
            order,
            operator=operator,
            request=request,
            auto_collect=collect_now,
            ticket_numbers=parsed_numbers,
        )

    log_action(
        operator,
        'Offline Sale',
        'ticketing',
        order.order_number,
        f'Penjualan OFFLINE {quantity} tiket {ticket_type.name}',
        metadata={
            'paid': is_paid,
            'collect_now': collect_now,
            'payment_id': getattr(payment, 'pk', None),
            'ticket_numbers': parsed_numbers or [],
        },
        request=request,
    )
    return order


@transaction.atomic
def mark_ticket_collected(ticket, operator, request=None):
    ticket = Ticket.objects.select_for_update().select_related('order', 'participant', 'ticket_type').get(pk=ticket.pk)
    if ticket.collection_status == Ticket.CollectionStatus.COLLECTED:
        raise ValueError(f'Tiket {ticket.ticket_number} sudah pernah diambil.')
    if ticket.status == Ticket.Status.CANCELLED:
        raise ValueError('Tiket dibatalkan.')
    if ticket.status not in (Ticket.Status.ISSUED, Ticket.Status.PAID, Ticket.Status.USED):
        raise ValueError('Tiket belum diterbitkan.')

    ticket.collection_status = Ticket.CollectionStatus.COLLECTED
    ticket.collected_at = timezone.now()
    ticket.collected_by = operator
    ticket.save(update_fields=['collection_status', 'collected_at', 'collected_by'])
    log_action(
        operator,
        'Ticket Collection',
        'ticketing',
        ticket.ticket_number,
        f'Tiket fisik {ticket.ticket_number} diserahkan',
        metadata={'order': ticket.order.order_number, 'channel': ticket.sales_channel},
        request=request,
    )
    return ticket


@transaction.atomic
def delete_order(order, operator, request=None):
    order_number = order.order_number
    order_status = order.status
    ticket_count = order.tickets.count()
    ticket_ids = list(order.tickets.values_list('ticket_number', flat=True))
    order.tickets.all().delete()
    order.delete()
    log_action(
        operator,
        'Delete Order',
        'ticketing',
        order_number,
        f'Hapus order {order_number} ({ticket_count} tiket)',
        metadata={'tickets': ticket_ids, 'status': order_status},
        request=request,
    )
    return order_number
