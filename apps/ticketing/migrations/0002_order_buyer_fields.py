from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ticketing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='buyer_name',
            field=models.CharField(default='', max_length=150, verbose_name='Nama Pembeli'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='buyer_email',
            field=models.EmailField(default='', max_length=254, verbose_name='Email Pembeli'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='buyer_phone',
            field=models.CharField(default='', max_length=20, verbose_name='No. WhatsApp'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='order',
            name='channel',
            field=models.CharField(choices=[('ONLINE', 'Online'), ('OFFLINE', 'Offline')], default='ONLINE', max_length=10),
        ),
        migrations.AlterField(
            model_name='order',
            name='total_amount',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Menunggu Pembayaran'),
                    ('WAITING_PAYMENT', 'Menunggu Pembayaran'),
                    ('WAITING_VERIFICATION', 'Menunggu Verifikasi'),
                    ('PAID', 'Lunas'),
                    ('CANCELLED', 'Dibatalkan'),
                    ('REJECTED', 'Ditolak'),
                ],
                default='PENDING',
                max_length=25,
            ),
        ),
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ['-created_at']},
        ),
    ]
