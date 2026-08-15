from urllib.parse import quote

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.payments.models import Payment, PaymentMethod

from .models import Order, TicketType
from .services import create_public_order, ticket_types_with_stats

ADMIN_WHATSAPP = '628988922983'


def _build_admin_wa_url(order, payment=None):
    amount = f'{order.total_amount:,.0f}'.replace(',', '.')
    lines = [
        f'*Notifikasi Pembayaran Teater Peace*',
        f'Order: {order.order_number}',
        f'Pembeli: {order.buyer_name}',
        f'WhatsApp: {order.buyer_phone}',
        f'Total: Rp {amount}',
        f'Jumlah: {order.quantity} tiket',
        f'Status: Menunggu Verifikasi',
    ]
    if payment and payment.payment_method_id:
        lines.append(f'Metode: {payment.payment_method.name}')
    if payment and payment.proof_submitted_at:
        lines.append(
            f'Waktu bukti: {timezone.localtime(payment.proof_submitted_at).strftime("%d/%m/%Y %H:%M")}'
        )
    lines.append('Mohon segera diverifikasi.')
    text = '\n'.join(lines)
    return f'https://wa.me/{ADMIN_WHATSAPP}?text={quote(text)}'


def ticket_select(request):
    types = ticket_types_with_stats(active_only=True)
    ticket_types = [tt for tt in types if tt.remaining > 0]
    return render(request, 'public/ticket_select.html', {'ticket_types': ticket_types})


def checkout(request):
    if request.method != 'POST':
        return redirect('public_order:ticket_select')

    stats_map = {tt.id: tt for tt in ticket_types_with_stats(active_only=True)}
    ticket_types = TicketType.objects.filter(active=True)
    payment_methods = PaymentMethod.objects.filter(active=True)

    items = []
    total = 0
    for tt in ticket_types:
        qty = int(request.POST.get(f'qty_{tt.id}', 0))
        if qty > 0:
            stat = stats_map.get(tt.id)
            remaining = stat.remaining if stat else tt.remaining
            if qty > remaining:
                messages.error(request, f'Kuota tiket "{tt.name}" tidak mencukupi.')
                return redirect('public_order:ticket_select')
            subtotal = tt.calculate_subtotal(qty)
            items.append({'type': tt, 'qty': qty, 'subtotal': subtotal})
            total += subtotal

    if not items:
        messages.error(request, 'Pilih minimal satu tiket.')
        return redirect('public_order:ticket_select')

        request.session['buyer_phone'] = buyer_phone
        request.session['buyer_email'] = buyer_email
        request.session['cart'] = [
            {'type_id': i['type'].id, 'qty': i['qty']} for i in items
        ]

        return render(request, 'public/checkout.html', {
            'items': items,
            'total': total,
            'payment_methods': payment_methods,
        })


def order_confirm(request, order_number):
    if request.method == 'POST' and order_number == 'new':
        buyer_name = request.POST.get('buyer_name', '').strip()
        buyer_email = request.POST.get('buyer_email', '').strip()
        buyer_phone = request.POST.get('buyer_phone', '').strip()
        payment_method_id = request.POST.get('payment_method', '')

        if not all([buyer_name, buyer_email, buyer_phone]):
            messages.error(request, 'Semua data pembeli harus diisi.')
            return redirect('public_order:ticket_select')

        cart = request.session.get('cart', [])
        if not cart:
            messages.error(request, 'Keranjang kosong.')
            return redirect('public_order:ticket_select')

        payment_method = None
        if payment_method_id:
            payment_method = PaymentMethod.objects.filter(id=payment_method_id, active=True).first()
        items = []
        for item in cart:
            ticket_type = TicketType.objects.filter(id=item['type_id'], active=True).first()
            if ticket_type and item['qty'] > 0:
                items.append({'ticket_type': ticket_type, 'quantity': item['qty']})
        try:
            order = create_public_order(
                buyer_name=buyer_name,
                buyer_email=buyer_email,
                buyer_phone=buyer_phone,
                items=items,
                payment_method=payment_method,
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('public_order:ticket_select')
        request.session.pop('cart', None)
        request.session['buyer_name'] = buyer_name
        request.session['buyer_phone'] = buyer_phone
        request.session['buyer_email'] = buyer_email
        return redirect('public_order:order_confirm', order_number=order.order_number)

    order = get_object_or_404(
        Order.objects.prefetch_related('tickets__ticket_type', 'order_items__ticket_type'),
        order_number=order_number,
    )
    payment = order.payments.select_related('payment_method').order_by('-created_at').first()
    payment_method = payment.payment_method if payment else None
    notify_wa = request.session.pop('notify_wa_url', None)

    return render(request, 'public/order_confirm.html', {
        'order': order,
        'payment': payment,
        'payment_method': payment_method,
        'notify_wa_url': notify_wa,
        'can_download_receipt': order.status in (
            Order.Status.WAITING_VERIFICATION,
            Order.Status.PAID,
            Order.Status.WAITING_PAYMENT,
            Order.Status.PENDING,
        ),
    })


def upload_proof(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)

    if request.method == 'POST':
        proof_file = request.FILES.get('proof_file')
        if not proof_file:
            messages.error(request, 'Pilih file bukti transfer.')
            return redirect('public_order:upload_proof', order_number=order_number)

        allowed = ['image/jpeg', 'image/png', 'image/webp']
        if proof_file.content_type not in allowed:
            messages.error(request, 'File harus berupa gambar (JPG, PNG, WebP).')
            return redirect('public_order:upload_proof', order_number=order_number)

        if proof_file.size > 5 * 1024 * 1024:
            messages.error(request, 'Ukuran file maksimal 5MB.')
            return redirect('public_order:upload_proof', order_number=order_number)

        now = timezone.now()
        payment = order.payments.select_related('payment_method').order_by('-created_at').first()
        if payment:
            payment.proof_file = proof_file
            payment.status = Payment.Status.PENDING
            payment.proof_submitted_at = now
            payment.save(update_fields=['proof_file', 'status', 'proof_submitted_at', 'updated_at'])
        else:
            payment = Payment.objects.create(
                order=order,
                amount=order.total_amount,
                proof_file=proof_file,
                status=Payment.Status.PENDING,
                proof_submitted_at=now,
            )

        order.status = Order.Status.WAITING_VERIFICATION
        order.save(update_fields=['status', 'updated_at'])

        request.session['notify_wa_url'] = _build_admin_wa_url(order, payment)
        request.session['buyer_phone'] = order.buyer_phone
        request.session['buyer_email'] = order.buyer_email
        messages.success(request, 'Bukti transfer berhasil diunggah. Data Anda sudah tersimpan dan sedang diverifikasi panitia.')
        return redirect('public_order:order_confirm', order_number=order_number)

    return render(request, 'public/upload_proof.html', {'order': order})


def order_receipt(request, order_number):
    phone = (request.GET.get('p') or request.POST.get('phone') or '').strip()
    order = get_object_or_404(
        Order.objects.prefetch_related('tickets__ticket_type', 'order_items__ticket_type'),
        order_number=order_number,
    )
    if not phone or order.buyer_phone != phone:
        messages.error(request, 'Akses struk membutuhkan nomor WhatsApp yang cocok.')
        return redirect('public_order:order_status')

    payment = order.payments.select_related('payment_method').order_by('-created_at').first()
    return render(request, 'public/receipt.html', {
        'order': order,
        'payment': payment,
        'tickets': order.tickets.select_related('ticket_type').order_by('ticket_number'),
        'items': order.order_items.select_related('ticket_type'),
        'print_mode': request.GET.get('print') == '1',
    })


def order_status(request):
    order = None
    searched = False

    if request.method == 'POST' or request.GET.get('q'):
        searched = True
        order_number = (request.POST.get('order_number') or request.GET.get('q', '')).strip().upper()
        phone = (request.POST.get('phone') or request.GET.get('p', '')).strip()

        if order_number and phone:
            try:
                order = Order.objects.prefetch_related(
                    'tickets__ticket_type',
                    'payments',
                ).get(
                    order_number=order_number,
                    buyer_phone=phone,
                )
                request.session['buyer_phone'] = phone
            except Order.DoesNotExist:
                messages.error(request, 'Order tidak ditemukan. Periksa nomor order dan nomor WhatsApp.')

    return render(request, 'public/order_status.html', {'order': order, 'searched': searched})


def order_detail(request, order_number):
    phone = request.GET.get('p', '')
    order = get_object_or_404(
        Order.objects.prefetch_related('tickets__ticket_type'),
        order_number=order_number,
        buyer_phone=phone,
    )
    tickets = order.tickets.all()
    payment = order.payments.select_related('payment_method').order_by('-created_at').first()
    return render(request, 'public/order_detail.html', {
        'order': order,
        'tickets': tickets,
        'payment': payment,
    })


from django.db.models import Q

def my_history(request):
    phone = (request.POST.get('phone') or request.GET.get('p') or request.session.get('buyer_phone') or '').strip()
    email = (request.POST.get('email') or request.GET.get('e') or request.session.get('buyer_email') or '').strip()

    if request.user.is_authenticated:
        if not email and getattr(request.user, 'email', None):
            email = request.user.email
        if not phone and getattr(request.user, 'phone', None):
            phone = request.user.phone

    orders = []
    if phone or email:
        query = Order.objects.prefetch_related('tickets__ticket_type', 'payments', 'order_items__ticket_type')
        if phone and email:
            orders = query.filter(Q(buyer_phone=phone) | Q(buyer_email__iexact=email)).order_by('-created_at')
        elif phone:
            orders = query.filter(buyer_phone=phone).order_by('-created_at')
        elif email:
            orders = query.filter(buyer_email__iexact=email).order_by('-created_at')

        if phone:
            request.session['buyer_phone'] = phone
        if email:
            request.session['buyer_email'] = email
        if orders and getattr(orders[0], 'buyer_name', None):
            request.session['buyer_name'] = orders[0].buyer_name

    return render(request, 'public/my_history.html', {
        'orders': orders,
        'phone': phone,
        'email': email,
        'searched': bool(phone or email),
    })


def buyer_login(request):
    entered_phone = ''
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        entered_phone = phone
        if not phone:
            messages.error(request, 'Masukkan Nomor WhatsApp Anda.')
            return render(request, 'public/buyer_login.html')
        
        # Clean phone format
        clean = phone.replace(' ', '').replace('-', '').replace('+', '')
        
        # Search DB for matching buyer orders (exact or last 8 digits)
        query = Q(buyer_phone=phone) | Q(buyer_phone=clean)
        if len(clean) >= 8:
            query |= Q(buyer_phone__icontains=clean[-8:])
            
        existing_orders = Order.objects.filter(query)
        
        if not existing_orders.exists():
            messages.error(
                request, 
                f'❌ Nomor WhatsApp ({phone}) tidak ditemukan dalam database pesanan. Pastikan Anda memasukkan nomor yang sama saat memesan tiket.'
            )
            return render(request, 'public/buyer_login.html', {'entered_phone': entered_phone})
        
        latest_order = existing_orders.order_by('-created_at').first()
        
        request.session['buyer_phone'] = latest_order.buyer_phone
        request.session['buyer_logged_in'] = True
        request.session['buyer_name'] = latest_order.buyer_name
        if latest_order.buyer_email:
            request.session['buyer_email'] = latest_order.buyer_email
        
        messages.success(request, f'Selamat datang kembali, {latest_order.buyer_name}! Berhasil masuk ke Akun Pembeli.')
        return redirect('public_order:my_history')

    return render(request, 'public/buyer_login.html', {'entered_phone': entered_phone})


def buyer_logout(request):
    request.session.pop('buyer_phone', None)
    request.session.pop('buyer_logged_in', None)
    request.session.pop('buyer_name', None)
    request.session.pop('buyer_email', None)
    messages.success(request, 'Anda telah keluar dari Akun Pembeli.')
    return redirect('core:home')
