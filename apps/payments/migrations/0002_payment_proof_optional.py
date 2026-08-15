from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='proof_file',
            field=models.ImageField(blank=True, upload_to='payment_proofs/'),
        ),
    ]
