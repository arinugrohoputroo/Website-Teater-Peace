import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class ShowScript(models.Model):
    """Data naskah pertunjukan teater."""
    title = models.CharField(max_length=150, verbose_name='Judul Naskah')
    synopsis = models.TextField(blank=True, verbose_name='Sinopsis')
    cast = models.TextField(blank=True, verbose_name='Pemain / Cast')
    director = models.CharField(max_length=150, default='R. Pujiono', verbose_name='Sutradara')
    production_by = models.CharField(max_length=150, default='Teater Peace & Peace Forum', verbose_name='Production By')
    poster = models.ImageField(upload_to='posters/', blank=True, verbose_name='Poster Naskah')
    order = models.PositiveIntegerField(default=0, verbose_name='Urutan Tampil')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Naskah Pertunjukan'
        verbose_name_plural = 'Naskah Pertunjukan'

    def __str__(self):
        return self.title


class TicketType(models.Model):
    """Season / jenis tiket (Season 1, Season 2, Season 3)."""
    name = models.CharField(max_length=100)
    show_time = models.CharField(max_length=50, blank=True, verbose_name='Waktu Pertunjukan', help_text='Contoh: 08.30 - 11.30')
    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='Harga 1 Tiket')
    bundle_price = models.DecimalField(
        max_digits=12, decimal_places=0,
        verbose_name='Harga 2 Tiket (Bundling)',
        help_text='Harga untuk pembelian kelipatan 2 tiket',
    )
    quota = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    naskah_list = models.ManyToManyField(ShowScript, blank=True, related_name='ticket_types', verbose_name='Naskah yang Ditampilkan')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Season / Jenis Tiket'
        verbose_name_plural = 'Season / Jenis Tiket'

    def __str__(self):
        return self.name

    def calculate_subtotal(self, quantity):
        """Hitung subtotal dengan bundling kelipatan 2."""
        if quantity <= 0:
            return 0
        bundles = quantity // 2
        singles = quantity % 2
        return bundles * self.bundle_price + singles * self.price

    @property
    def sold_count(self):
        if hasattr(self, 'sold'):
            return self.sold
        return Ticket.objects.filter(
            ticket_type=self,
        ).exclude(status=Ticket.Status.CANCELLED).count()

    @property
    def remaining(self):
        if hasattr(self, 'remaining_qty'):
            return self.remaining_qty
        return max(0, self.quota - self.sold_count)


class Order(models.Model):
    class Channel(models.TextChoices):
        ONLINE = 'ONLINE', 'Online'
        OFFLINE = 'OFFLINE', 'Offline'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Menunggu Pembayaran'
        WAITING_PAYMENT = 'WAITING_PAYMENT', 'Menunggu Pembayaran'
        WAITING_VERIFICATION = 'WAITING_VERIFICATION', 'Menunggu Verifikasi'
        PAID = 'PAID', 'Lunas'
        CANCELLED = 'CANCELLED', 'Dibatalkan'
        REJECTED = 'REJECTED', 'Ditolak'

    order_number = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )
    buyer_name = models.CharField(max_length=150, verbose_name='Nama Pembeli')
    buyer_email = models.EmailField(blank=True, verbose_name='Email Pembeli')
    buyer_phone = models.CharField(max_length=20, verbose_name='No. WhatsApp')
    participant = models.ForeignKey(
        'participants.Participant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.ONLINE)
    total_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.PENDING,
    )
    ga_purchase_sent = models.BooleanField(default=False, verbose_name='GA4 Purchase Sent')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            if self.channel == self.Channel.OFFLINE:
                last = Order.objects.filter(channel=self.Channel.OFFLINE).order_by('-id').first()
                next_num = 1
                if last and last.order_number.startswith('TP-OFF-'):
                    try:
                        next_num = int(last.order_number.replace('TP-OFF-', '')) + 1
                    except ValueError:
                        next_num = Order.objects.filter(channel=self.Channel.OFFLINE).count() + 1
                else:
                    next_num = Order.objects.filter(channel=self.Channel.OFFLINE).count() + 1
                self.order_number = f'TP-OFF-{next_num:06d}'
            else:
                last = Order.objects.filter(channel=self.Channel.ONLINE).order_by('-id').first()
                next_num = 1
                if last:
                    raw = last.order_number
                    for prefix in ('TP-ON-', 'TP-2026-'):
                        if raw.startswith(prefix):
                            try:
                                next_num = int(raw.replace(prefix, '')) + 1
                            except ValueError:
                                next_num = Order.objects.filter(channel=self.Channel.ONLINE).count() + 1
                            break
                    else:
                        next_num = Order.objects.filter(channel=self.Channel.ONLINE).count() + 1
                self.order_number = f'TP-ON-{next_num:06d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number

    @property
    def quantity(self):
        return self.order_items.aggregate(total=models.Sum('quantity')).get('total') or 0

    @property
    def latest_payment(self):
        return self.payments.order_by('-created_at').first()

    @property
    def payment_submitted_at(self):
        payment = self.latest_payment
        if payment and payment.proof_submitted_at:
            return payment.proof_submitted_at
        return None

    @property
    def payment_status_label(self):
        payment = self.latest_payment
        if payment:
            return payment.get_status_display()
        return self.get_status_display()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f'{self.order.order_number} - {self.ticket_type.name} x{self.quantity}'


class Ticket(models.Model):
    class Status(models.TextChoices):
        RESERVED = 'RESERVED', 'Reserved'
        PAID = 'PAID', 'Paid'
        ISSUED = 'ISSUED', 'Issued'
        USED = 'USED', 'Used / Checked-in'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class Channel(models.TextChoices):
        ONLINE = 'ONLINE', 'Online'
        OFFLINE = 'OFFLINE', 'Offline'

    class CollectionStatus(models.TextChoices):
        NOT_COLLECTED = 'NOT_COLLECTED', 'Belum Diambil'
        COLLECTED = 'COLLECTED', 'Sudah Diambil'

    ticket_number = models.CharField(max_length=4, unique=True, verbose_name='ID Tiket')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tickets')
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
    )
    participant = models.ForeignKey(
        'participants.Participant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
    )
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT, related_name='tickets')
    sales_channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
        default=Channel.ONLINE,
        verbose_name='Channel',
    )
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ISSUED,
    )
    collection_status = models.CharField(
        max_length=20,
        choices=CollectionStatus.choices,
        default=CollectionStatus.NOT_COLLECTED,
    )
    collected_at = models.DateTimeField(null=True, blank=True)
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='collected_tickets',
    )
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ticket_number']
        constraints = [
            models.CheckConstraint(
                check=Q(ticket_number__gte='0001'),
                name='ticket_number_gte_0001',
            ),
        ]

    def __str__(self):
        return f'ID Tiket {self.ticket_number}'

    @property
    def is_checked_in(self):
        return self.status == self.Status.USED

    @property
    def payment_status(self):
        payment = self.order.payments.order_by('-created_at').first()
        if payment:
            return payment.status
        if self.order.status == Order.Status.PAID:
            return 'VERIFIED'
        return self.order.status

    @property
    def payment_status_display(self):
        payment = self.order.payments.order_by('-created_at').first()
        if payment:
            return payment.get_status_display()
        return self.order.get_status_display()
