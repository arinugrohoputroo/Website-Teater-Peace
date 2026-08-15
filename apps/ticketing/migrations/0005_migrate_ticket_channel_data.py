from django.db import migrations


def migrate_ticket_data(apps, schema_editor):
    Ticket = apps.get_model('ticketing', 'Ticket')
    for ticket in Ticket.objects.select_related('order').all():
        updates = []
        if ticket.status == 'ACTIVE':
            ticket.status = 'ISSUED'
            updates.append('status')
        if ticket.order_id:
            channel = ticket.order.channel
            if ticket.sales_channel != channel:
                ticket.sales_channel = channel
                updates.append('sales_channel')
            if channel == 'OFFLINE' and ticket.collection_status == 'NOT_COLLECTED':
                # existing offline tickets treated as already handed over if unknown
                pass
        if updates:
            ticket.save(update_fields=list(set(updates)))


class Migration(migrations.Migration):

    dependencies = [
        ('ticketing', '0004_ticket_channel_collection_status'),
    ]

    operations = [
        migrations.RunPython(migrate_ticket_data, migrations.RunPython.noop),
    ]
