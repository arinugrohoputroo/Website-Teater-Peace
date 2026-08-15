from django.core.management.base import BaseCommand

from apps.payments.models import PaymentMethod
from apps.ticketing.models import Ticket, TicketType


SMOKE_TICKET_NAMES = ['Reguler Smoke', 'Smoke Test', 'Test Ticket']
SMOKE_PAYMENT_NAMES = ['BCA Smoke', 'Smoke Payment', 'Test Payment']


class Command(BaseCommand):
    help = 'Hapus/nonaktifkan data smoke test (Reguler Smoke, dll).'

    def handle(self, *args, **options):
        removed_tickets = 0
        deactivated_tickets = 0
        for name in SMOKE_TICKET_NAMES:
            ticket_type = TicketType.objects.filter(name=name).first()
            if not ticket_type:
                continue
            has_refs = Ticket.objects.filter(ticket_type=ticket_type).exists()
            if has_refs:
                ticket_type.active = False
                ticket_type.save(update_fields=['active'])
                deactivated_tickets += 1
            else:
                ticket_type.delete()
                removed_tickets += 1

        removed_payments = 0
        deactivated_payments = 0
        for name in SMOKE_PAYMENT_NAMES:
            method = PaymentMethod.objects.filter(name=name).first()
            if not method:
                continue
            if method.payment_set.exists():
                method.active = False
                method.save(update_fields=['active'])
                deactivated_payments += 1
            else:
                method.delete()
                removed_payments += 1

        self.stdout.write(self.style.SUCCESS(
            f'Cleanup selesai. Ticket hapus: {removed_tickets}, nonaktif: {deactivated_tickets}, '
            f'Payment hapus: {removed_payments}, nonaktif: {deactivated_payments}'
        ))
