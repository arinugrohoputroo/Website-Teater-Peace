import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('participants', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('snacks', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommitteeMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('normalized_name', models.CharField(db_index=True, max_length=255)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Anggota Panitia',
                'verbose_name_plural': 'Anggota Panitia',
                'ordering': ['name'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='snackclaim',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='snackclaim',
            name='committee_member',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='snack_claims',
                to='snacks.committeemember',
            ),
        ),
        migrations.AddField(
            model_name='snackclaim',
            name='detection_method',
            field=models.CharField(
                choices=[('OCR', 'OCR'), ('QR', 'QR'), ('MANUAL', 'Manual')],
                default='OCR',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='snackclaim',
            name='ocr_confidence',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='snackclaim',
            name='ocr_text',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='snackclaim',
            name='participant',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='participants.participant',
            ),
        ),
        migrations.AddConstraint(
            model_name='snackclaim',
            constraint=models.UniqueConstraint(
                condition=models.Q(('committee_member__isnull', False)),
                fields=('committee_member', 'session'),
                name='unique_committee_session_snack',
            ),
        ),
        migrations.AddConstraint(
            model_name='snackclaim',
            constraint=models.UniqueConstraint(
                condition=models.Q(('participant__isnull', False)),
                fields=('participant', 'session'),
                name='unique_participant_session_snack',
            ),
        ),
    ]
