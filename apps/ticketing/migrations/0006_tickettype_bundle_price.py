from decimal import Decimal

from django.db import migrations, models


SEASON_PRICES = {
    'Season 1': (Decimal('8000'), Decimal('15000')),
    'Season 2': (Decimal('10000'), Decimal('18000')),
    'Season 3': (Decimal('15000'), Decimal('25000')),
}


def set_season_prices(apps, schema_editor):
    TicketType = apps.get_model('ticketing', 'TicketType')
    for name, (price, bundle_price) in SEASON_PRICES.items():
        updated = TicketType.objects.filter(name=name).update(price=price, bundle_price=bundle_price)
        if not updated:
            TicketType.objects.create(
                name=name,
                price=price,
                bundle_price=bundle_price,
                quota=1000,
                active=True,
            )
    for tt in TicketType.objects.filter(bundle_price=0):
        TicketType.objects.filter(pk=tt.pk).update(bundle_price=tt.price * 2)


class Migration(migrations.Migration):

    dependencies = [
        ('ticketing', '0005_migrate_ticket_channel_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='tickettype',
            name='bundle_price',
            field=models.DecimalField(
                decimal_places=0,
                default=0,
                help_text='Harga untuk pembelian kelipatan 2 tiket',
                max_digits=12,
                verbose_name='Harga 2 Tiket (Bundling)',
            ),
        ),
        migrations.RunPython(set_season_prices, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='tickettype',
            name='price',
            field=models.DecimalField(decimal_places=0, max_digits=12, verbose_name='Harga 1 Tiket'),
        ),
    ]
