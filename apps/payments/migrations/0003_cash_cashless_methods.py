from django.db import migrations, models


def seed_offline_methods(apps, schema_editor):
    PaymentMethod = apps.get_model('payments', 'PaymentMethod')
    defaults = [
        ('Tunai', 'CASH'),
        ('Cashless', 'CASHLESS'),
    ]
    for name, ptype in defaults:
        method = PaymentMethod.objects.filter(name__iexact=name).first()
        if method:
            method.type = ptype
            method.active = True
            method.save()
        else:
            PaymentMethod.objects.create(
                name=name,
                type=ptype,
                active=True,
                account_number='',
                account_name='',
                instructions='',
            )


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_payment_proof_optional'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentmethod',
            name='type',
            field=models.CharField(
                choices=[
                    ('BANK', 'Bank Transfer'),
                    ('QRIS', 'QRIS'),
                    ('CASH', 'Tunai'),
                    ('CASHLESS', 'Cashless'),
                    ('OTHER', 'Lainnya'),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(seed_offline_methods, migrations.RunPython.noop),
    ]
