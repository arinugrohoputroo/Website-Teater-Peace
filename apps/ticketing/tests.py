from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.payments.models import PaymentMethod
from apps.ticketing.models import Ticket, TicketType
from apps.ticketing.services import (
    create_offline_order,
    create_public_order,
    issue_tickets_for_order,
    mark_ticket_collected,
)


class ChannelCollectionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='admin',
            email='admin@example.com',
            name='Admin',
            password='password123',
            role='ADMIN',
            is_staff=True,
            is_superuser=True,
        )
        self.s1 = TicketType.objects.create(name='Season 1', price=8000, bundle_price=15000, quota=1000, active=True)
        self.s2 = TicketType.objects.create(name='Season 2', price=10000, bundle_price=18000, quota=1000, active=True)
        self.s3 = TicketType.objects.create(name='Season 3', price=15000, bundle_price=25000, quota=1000, active=True)
        self.payment_method = PaymentMethod.objects.create(name='BCA', type='BANK', account_number='123')

    def test_online_two_tickets_not_collected(self):
        order = create_public_order(
            buyer_name='Budi',
            buyer_email='budi@example.com',
            buyer_phone='08123',
            items=[{'ticket_type': self.s1, 'quantity': 2}],
            payment_method=self.payment_method,
        )
        payment = order.payments.first()
        payment.status = 'VERIFIED'
        payment.save(update_fields=['status'])
        issued = issue_tickets_for_order(order, operator=self.user)
        self.assertEqual([t.ticket_number for t in issued], ['0001', '0002'])
        self.assertTrue(all(t.sales_channel == 'ONLINE' for t in issued))
        self.assertTrue(all(t.collection_status == 'NOT_COLLECTED' for t in issued))
        self.assertTrue(order.order_number.startswith('TP-ON-'))

    def test_online_then_offline_global_sequence(self):
        order1 = create_public_order(
            buyer_name='Budi',
            buyer_email='budi@example.com',
            buyer_phone='08123',
            items=[{'ticket_type': self.s2, 'quantity': 1}],
            payment_method=self.payment_method,
        )
        p1 = order1.payments.first()
        p1.status = 'VERIFIED'
        p1.save(update_fields=['status'])
        issue_tickets_for_order(order1, operator=self.user)

        order2 = create_offline_order(
            buyer_name='Ani',
            buyer_email='ani@example.com',
            buyer_phone='08124',
            ticket_type=self.s3,
            quantity=2,
            payment_method=self.payment_method,
            is_paid=True,
            collect_now=True,
            operator=self.user,
        )
        nums = list(order2.tickets.values_list('ticket_number', flat=True))
        self.assertEqual(nums, ['0002', '0003'])
        self.assertTrue(order2.order_number.startswith('TP-OFF-'))
        self.assertTrue(all(t.sales_channel == 'OFFLINE' for t in order2.tickets.all()))
        self.assertTrue(all(t.collection_status == 'COLLECTED' for t in order2.tickets.all()))

    def test_collection_keeps_issued_status(self):
        order = create_offline_order(
            buyer_name='Budi',
            buyer_email='budi@example.com',
            buyer_phone='08123',
            ticket_type=self.s1,
            quantity=1,
            payment_method=self.payment_method,
            is_paid=True,
            collect_now=False,
            operator=self.user,
        )
        ticket = order.tickets.first()
        self.assertEqual(ticket.collection_status, 'NOT_COLLECTED')
        mark_ticket_collected(ticket, self.user)
        ticket.refresh_from_db()
        self.assertEqual(ticket.collection_status, 'COLLECTED')
        self.assertEqual(ticket.status, 'ISSUED')


class BundlingPriceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='bundling-admin',
            email='bundling@example.com',
            name='Admin',
            password='password123',
            role='ADMIN',
            is_staff=True,
        )
        self.s1 = TicketType.objects.create(name='Season 1', price=8000, bundle_price=15000, quota=1000, active=True)
        self.s2 = TicketType.objects.create(name='Season 2', price=10000, bundle_price=18000, quota=1000, active=True)
        self.s3 = TicketType.objects.create(name='Season 3', price=15000, bundle_price=25000, quota=1000, active=True)
        self.payment_method = PaymentMethod.objects.create(name='BCA', type='BANK', account_number='123')

    def test_calculate_subtotal_examples(self):
        cases = [
            (self.s1, 1, 8000), (self.s1, 2, 15000), (self.s1, 3, 23000), (self.s1, 6, 45000),
            (self.s2, 1, 10000), (self.s2, 2, 18000), (self.s2, 3, 28000), (self.s2, 6, 54000),
            (self.s3, 1, 15000), (self.s3, 2, 25000), (self.s3, 3, 40000), (self.s3, 6, 75000),
        ]
        for ticket_type, qty, expected in cases:
            self.assertEqual(ticket_type.calculate_subtotal(qty), expected)

    def test_order_uses_bundling_total(self):
        order = create_public_order(
            buyer_name='Budi',
            buyer_email='budi@example.com',
            buyer_phone='08123',
            items=[{'ticket_type': self.s1, 'quantity': 3}],
            payment_method=self.payment_method,
        )
        self.assertEqual(order.total_amount, 23000)
        item = order.order_items.first()
        self.assertEqual(item.subtotal, 23000)

    def test_offline_order_bundling(self):
        order = create_offline_order(
            buyer_name='Ani',
            buyer_email='ani@example.com',
            buyer_phone='08124',
            ticket_type=self.s2,
            quantity=5,
            ticket_numbers=['0101', '0102', '0103', '0104', '0105'],
            payment_method=self.payment_method,
            is_paid=False,
            collect_now=False,
            operator=None,
        )
        self.assertEqual(order.total_amount, 46000)

    def test_offline_custom_ticket_numbers(self):
        order = create_offline_order(
            buyer_name='Ani',
            buyer_email='ani@example.com',
            buyer_phone='08124',
            ticket_type=self.s1,
            quantity=2,
            ticket_numbers='0050, 0088',
            payment_method=self.payment_method,
            is_paid=True,
            collect_now=True,
            operator=self.user if hasattr(self, 'user') else None,
        )
        nums = sorted(order.tickets.values_list('ticket_number', flat=True))
        self.assertEqual(nums, ['0050', '0088'])


class CollectionAndDeleteTests(TestCase):
    def setUp(self):
        from django.test import Client
        from django.urls import reverse

        self.client = Client(HTTP_HOST='127.0.0.1')
        self.reverse = reverse
        self.user = get_user_model().objects.create_user(
            username='admin2',
            email='admin2@example.com',
            name='Admin',
            password='password123',
            role='ADMIN',
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(self.user)
        self.s1 = TicketType.objects.create(name='Season 1', price=8000, bundle_price=15000, quota=1000, active=True)
        self.payment_method = PaymentMethod.objects.create(name='BCA', type='BANK', account_number='123')

    def test_collection_ticket_click_stays_on_page(self):
        order = create_public_order(
            buyer_name='Budi',
            buyer_email='budi@example.com',
            buyer_phone='08123',
            items=[{'ticket_type': self.s1, 'quantity': 1}],
            payment_method=self.payment_method,
        )
        payment = order.payments.first()
        payment.status = 'VERIFIED'
        payment.save(update_fields=['status'])
        issue_tickets_for_order(order, operator=self.user)
        ticket = order.tickets.first()
        url = self.reverse('ticketing:collection') + f'?ticket={ticket.ticket_number}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ticket.ticket_number)
        self.assertContains(response, 'SERAHKAN TIKET FISIK')

    def test_delete_junk_order(self):
        from apps.ticketing.models import Order
        from apps.ticketing.services import delete_order

        order = create_public_order(
            buyer_name='Sampah',
            buyer_email='',
            buyer_phone='08111',
            items=[{'ticket_type': self.s1, 'quantity': 1}],
            payment_method=self.payment_method,
        )
        order_number = order.order_number
        delete_order(order, self.user)
        self.assertFalse(Order.objects.filter(order_number=order_number).exists())

    def test_can_delete_paid_order_with_tickets(self):
        from apps.ticketing.models import Order

        order = create_offline_order(
            buyer_name='Budi',
            buyer_email='',
            buyer_phone='08123',
            ticket_type=self.s1,
            quantity=1,
            ticket_numbers=['0077'],
            payment_method=self.payment_method,
            is_paid=True,
            collect_now=False,
            operator=self.user,
        )
        order_number = order.order_number
        response = self.client.post(self.reverse('ticketing:order_delete', args=[order_number]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Order.objects.filter(order_number=order_number).exists())
        self.assertFalse(Ticket.objects.filter(ticket_number='0077').exists())
