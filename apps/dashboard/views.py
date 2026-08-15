from django.db.models import Sum

from django.shortcuts import render

from apps.accounts.decorators import panitia_required
from apps.payments.models import Payment
from apps.snacks.models import CommitteeMember, SnackClaim, SnackSession
from apps.ticketing.models import Order, Ticket
from apps.ticketing.services import get_max_tickets, get_quota_summary


@panitia_required
def index(request):
    recent_orders = Order.objects.prefetch_related('order_items', 'tickets').order_by('-created_at')[:5]
    pending_payments = Payment.objects.select_related('order', 'payment_method').filter(status='PENDING').order_by('-created_at')[:5]
    recent_snacks = SnackClaim.objects.select_related('committee_member', 'session', 'operator').filter(
        committee_member__isnull=False,
    ).order_by('-claimed_at')[:5]
    snack_stats = {
        'total_committee': CommitteeMember.objects.filter(active=True).count(),
        'active_sessions': SnackSession.objects.filter(active=True).count(),
        'claimed_count': SnackClaim.objects.filter(committee_member__isnull=False).values('committee_member_id').distinct().count(),
    }
    snack_stats['unclaimed_count'] = max(0, snack_stats['total_committee'] - snack_stats['claimed_count'])

    tickets = Ticket.objects.exclude(status=Ticket.Status.CANCELLED)
    online_sold = tickets.filter(sales_channel='ONLINE').count()
    offline_sold = tickets.filter(sales_channel='OFFLINE').count()
    tickets_sold = tickets.count()
    online_not_collected = tickets.filter(sales_channel='ONLINE', collection_status='NOT_COLLECTED').count()
    offline_not_collected = tickets.filter(sales_channel='OFFLINE', collection_status='NOT_COLLECTED').count()
    collected = tickets.filter(collection_status='COLLECTED').count()
    cancelled = Ticket.objects.filter(status=Ticket.Status.CANCELLED).count()
    revenue = Payment.objects.filter(status='VERIFIED').aggregate(total=Sum('amount')).get('total') or 0

    quota = get_quota_summary()
    max_tickets = get_max_tickets()

    context = {
        'total_tickets': quota['total_quota'],
        'tickets_sold': tickets_sold,
        'tickets_remaining': quota['total_remaining'],
        'id_pool_total': max_tickets,
        'id_pool_remaining': max(0, max_tickets - tickets_sold),
        'season_stats': quota['types'],
        'online_sold': online_sold,
        'offline_sold': offline_sold,
        'online_not_collected': online_not_collected,
        'offline_not_collected': offline_not_collected,
        'collected': collected,
        'cancelled': cancelled,
        'revenue': revenue,
        'snacks_today': SnackClaim.objects.count(),
        'pending_payments_count': Payment.objects.filter(status='PENDING').count(),
        'recent_orders': recent_orders,
        'pending_payments': pending_payments,
        'recent_snacks': recent_snacks,
        'snack_stats': snack_stats,
    }
    return render(request, 'dashboard/index.html', context)
