from django.contrib import admin

from .models import Order, OrderItem, Ticket, TicketType


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('subtotal',)


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 0
    readonly_fields = ('ticket_number', 'qr_token', 'issued_at')
    fields = ('ticket_number', 'ticket_type', 'sales_channel', 'status', 'collection_status', 'qr_token')


@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'bundle_price', 'quota', 'active', 'created_at')
    list_filter = ('active',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'buyer_name', 'buyer_phone', 'channel', 'quantity', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'channel')
    search_fields = ('order_number', 'buyer_name', 'buyer_phone', 'buyer_email')
    inlines = [OrderItemInline, TicketInline]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'ticket_number',
        'ticket_type',
        'sales_channel',
        'order',
        'status',
        'collection_status',
        'issued_at',
    )
    list_filter = ('sales_channel', 'status', 'collection_status', 'ticket_type')
    search_fields = ('ticket_number', 'order__order_number', 'participant__name', 'order__buyer_name')
    readonly_fields = ('qr_token', 'issued_at', 'collected_at')
