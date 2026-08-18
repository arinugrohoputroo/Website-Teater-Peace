from urllib.parse import quote



from django.contrib import messages

from django.db.models import Q

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

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





def _cart_items_from_session(request):

    cart = request.session.get('cart', [])

    if not cart:

        return [], 0

    items = []

    total = 0

    for entry in cart:

        ticket_type = TicketType.objects.filter(id=entry.get('type_id'), active=True).first()

        qty = int(entry.get('qty') or 0)

        if ticket_type and qty > 0:

            subtotal = ticket_type.calculate_subtotal(qty)

            items.append({'type': ticket_type, 'qty': qty, 'subtotal': subtotal})

            total += subtotal

    return items, total





def _render_checkout(request, items=None, total=None, form_data=None):

    if items is None or total is None:

        items, total = _cart_items_from_session(request)

    if not items:

        messages.error(request, 'Keranjang kosong.')

        return redirect('public_order:ticket_select')

    form_data = form_data or {}

    return render(request, 'public/checkout.html', {

        'items': items,

        'total': total,

        'payment_methods': PaymentMethod.objects.filter(active=True),

        'form_buyer_name': form_data.get('buyer_name', ''),

        'form_buyer_phone': form_data.get('buyer_phone', ''),

        'form_buyer_email': form_data.get('buyer_email', ''),

        'form_payment_method': form_data.get('payment_method', ''),

    })





def ticket_select(request):
    types = TicketType.objects.filter(active=True).prefetch_related('naskah_list')
    stats_map = {tt.id: tt for tt in ticket_types_with_stats(active_only=True)}
    ticket_types = []
    for tt in types:
        stat = stats_map.get(tt.id)
        tt.remaining_qty = stat.remaining if stat else tt.remaining
        if tt.remaining_qty > 0:
            ticket_types.append(tt)
    return render(request, 'public/ticket_select.html', {'ticket_types': ticket_types})





def checkout(request):

    if request.method == 'GET':

        return _render_checkout(request)



    if request.method != 'POST':

        return redirect('public_order:ticket_select')



    stats_map = {tt.id: tt for tt in ticket_types_with_stats(active_only=True)}

    ticket_types = TicketType.objects.filter(active=True)



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



    request.session['cart'] = [

        {'type_id': i['type'].id, 'qty': i['qty']} for i in items

    ]



    return _render_checkout(request, items=items, total=total)





def order_confirm(request, order_number):

    if request.method == 'POST' and order_number == 'new':

        buyer_name = request.POST.get('buyer_name', '').strip()

        buyer_email = request.POST.get('buyer_email', '').strip()

        buyer_phone = request.POST.get('buyer_phone', '').strip()

        payment_method_id = request.POST.get('payment_method', '')



        form_data = {

            'buyer_name': buyer_name,

            'buyer_phone': buyer_phone,

            'buyer_email': buyer_email,

            'payment_method': payment_method_id,

        }



        if not buyer_name or not buyer_phone:

            messages.error(request, 'Nama lengkap dan nomor WhatsApp wajib diisi.')

            return _render_checkout(request, form_data=form_data)



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

            return _render_checkout(request, form_data=form_data)

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

    phone = (request.POST.get('phone') or request.GET.get('p') or '').strip()

    if phone:

        return redirect(f"{reverse('public_order:my_history')}?p={phone}")

    return redirect('public_order:my_history')





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

            messages.error(request, 'Masukkan nomor WhatsApp Anda.')

            return render(request, 'public/buyer_login.html')



        clean = phone.replace(' ', '').replace('-', '').replace('+', '')

        query = Q(buyer_phone=phone) | Q(buyer_phone=clean)

        if len(clean) >= 8:

            query |= Q(buyer_phone__icontains=clean[-8:])



        existing_orders = Order.objects.filter(query)



        if not existing_orders.exists():

            messages.error(

                request,

                'Nomor WhatsApp ini belum terdaftar pada pesanan manapun. Silakan beli tiket terlebih dahulu.'

            )

            return render(request, 'public/buyer_login.html', {'entered_phone': entered_phone})



        latest_order = existing_orders.order_by('-created_at').first()



        request.session['buyer_phone'] = latest_order.buyer_phone

        request.session['buyer_logged_in'] = True

        request.session['buyer_name'] = latest_order.buyer_name

        if latest_order.buyer_email:

            request.session['buyer_email'] = latest_order.buyer_email



        messages.success(request, f'Selamat datang, {latest_order.buyer_name}.')

        return redirect('public_order:my_history')



    return render(request, 'public/buyer_login.html', {'entered_phone': entered_phone})





def buyer_logout(request):

    request.session.pop('buyer_phone', None)

    request.session.pop('buyer_logged_in', None)

    request.session.pop('buyer_name', None)

    request.session.pop('buyer_email', None)

    messages.success(request, 'Anda telah keluar dari Akun Pembeli.')

    return redirect('core:home')

