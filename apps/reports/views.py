import csv



from django.db.models import Sum

from django.http import HttpResponse

from django.shortcuts import render



from apps.accounts.decorators import module_required

from apps.payments.models import Payment

from apps.snacks.models import SnackClaim

from apps.ticketing.models import Order, Ticket





@module_required('report')

def index(request):

    online_tickets = Ticket.objects.filter(sales_channel='ONLINE').exclude(status='CANCELLED')

    offline_tickets = Ticket.objects.filter(sales_channel='OFFLINE').exclude(status='CANCELLED')

    online_orders = Order.objects.filter(channel='ONLINE', status='PAID')

    offline_orders = Order.objects.filter(channel='OFFLINE', status='PAID')



    not_collected = Ticket.objects.filter(

        collection_status='NOT_COLLECTED',

    ).exclude(status='CANCELLED').select_related('order', 'participant', 'ticket_type').order_by('ticket_number')



    context = {

        'sales_total': Order.objects.filter(status='PAID').aggregate(total=Sum('total_amount')).get('total') or 0,

        'online_count': online_tickets.count(),

        'offline_count': offline_tickets.count(),

        'online_revenue': online_orders.aggregate(total=Sum('total_amount')).get('total') or 0,

        'offline_revenue': offline_orders.aggregate(total=Sum('total_amount')).get('total') or 0,

        'online_collected': online_tickets.filter(collection_status='COLLECTED').count(),

        'online_not_collected': online_tickets.filter(collection_status='NOT_COLLECTED').count(),

        'offline_collected': offline_tickets.filter(collection_status='COLLECTED').count(),

        'offline_not_collected': offline_tickets.filter(collection_status='NOT_COLLECTED').count(),

        'verified_payment_count': Payment.objects.filter(status='VERIFIED').count(),

        'ticket_count': Ticket.objects.exclude(status='CANCELLED').count(),

        'snack_count': SnackClaim.objects.count(),

        'orders': Order.objects.order_by('-created_at')[:20],

        'not_collected': not_collected[:100],

    }

    return render(request, 'reports/index.html', context)





@module_required('report')

def sales_csv(request):

    response = HttpResponse(content_type='text/csv')

    response['Content-Disposition'] = 'attachment; filename="teater-peace-sales.csv"'

    writer = csv.writer(response)

    writer.writerow([

        'ID Ticket', 'Order', 'Pembeli', 'WhatsApp', 'Season', 'Channel',

        'Payment', 'Collection', 'Total Order',

    ])

    for ticket in Ticket.objects.select_related('order', 'participant', 'ticket_type').order_by('ticket_number'):

        writer.writerow([

            ticket.ticket_number,

            ticket.order.order_number,

            ticket.order.buyer_name,

            ticket.order.buyer_phone,

            ticket.ticket_type.name,

            ticket.sales_channel,

            ticket.payment_status_display,

            ticket.get_collection_status_display(),

            ticket.order.total_amount,

        ])

    return response





@module_required('report')

def not_collected_csv(request):

    response = HttpResponse(content_type='text/csv')

    response['Content-Disposition'] = 'attachment; filename="tiket-belum-diambil.csv"'

    writer = csv.writer(response)

    writer.writerow(['ID Ticket', 'Nama', 'Season', 'Order', 'Channel', 'Status'])

    qs = Ticket.objects.filter(collection_status='NOT_COLLECTED').exclude(status='CANCELLED').select_related(

        'order', 'participant', 'ticket_type'

    ).order_by('ticket_number')

    for ticket in qs:

        writer.writerow([

            ticket.ticket_number,

            ticket.participant.name if ticket.participant else ticket.order.buyer_name,

            ticket.ticket_type.name,

            ticket.order.order_number,

            ticket.sales_channel,

            'BELUM DIAMBIL',

        ])

    return response

