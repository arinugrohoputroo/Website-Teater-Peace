from django.conf import settings
from django.db import models


class PaymentMethod(models.Model):
    class Type(models.TextChoices):
        BANK = 'BANK', 'Bank Transfer'
        QRIS = 'QRIS', 'QRIS'
        CASH = 'CASH', 'Tunai'
        CASHLESS = 'CASHLESS', 'Cashless'
        OTHER = 'OTHER', 'Lainnya'

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=Type.choices)
    account_number = models.CharField(max_length=50, blank=True)
    account_name = models.CharField(max_length=100, blank=True)
    qr_image = models.ImageField(upload_to='payment_qr/', blank=True)
    instructions = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    class Meta:
        verbose_name = 'Metode Pembayaran'
        verbose_name_plural = 'Metode Pembayaran'


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Menunggu Verifikasi'
        VERIFIED = 'VERIFIED', 'Terverifikasi'
        REJECTED = 'REJECTED', 'Ditolak'

    order = models.ForeignKey('ticketing.Order', on_delete=models.CASCADE, related_name='payments')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    proof_file = models.ImageField(upload_to='payment_proofs/', blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_payments'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    proof_submitted_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment #{self.pk} - {self.order}"

    class Meta:
        verbose_name = 'Pembayaran'
        verbose_name_plural = 'Pembayaran'
