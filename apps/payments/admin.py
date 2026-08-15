from django.contrib import admin

from .models import Payment, PaymentMethod


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'account_number', 'active')
    list_filter = ('type', 'active')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    readonly_fields = ('created_at', 'updated_at')
