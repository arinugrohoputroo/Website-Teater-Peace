# Generated manually for QR snack scanner

from django.db import migrations, models


def backfill_codes_and_tokens(apps, schema_editor):
    CommitteeMember = apps.get_model('snacks', 'CommitteeMember')
    import secrets
    import string

    alphabet = string.ascii_uppercase + string.digits
    alphabet = alphabet.replace('O', '').replace('0', '').replace('I', '').replace('1', '')

    def make_token():
        body = ''.join(secrets.choice(alphabet) for _ in range(8))
        return f'TP26-{body}'

    used_tokens = set(CommitteeMember.objects.exclude(qr_token='').values_list('qr_token', flat=True))
    used_codes = set(CommitteeMember.objects.exclude(member_code='').values_list('member_code', flat=True))
    next_num = 1
    for member in CommitteeMember.objects.order_by('id'):
        fields = []
        if not member.member_code:
            while f'P{next_num:03d}' in used_codes:
                next_num += 1
            member.member_code = f'P{next_num:03d}'
            used_codes.add(member.member_code)
            next_num += 1
            fields.append('member_code')
        if not member.qr_token:
            token = make_token()
            while token in used_tokens:
                token = make_token()
            member.qr_token = token
            used_tokens.add(token)
            fields.append('qr_token')
        if fields:
            member.save(update_fields=fields)


class Migration(migrations.Migration):

    dependencies = [
        ('snacks', '0002_committee_member_ocr_scanner'),
    ]

    operations = [
        migrations.AddField(
            model_name='committeemember',
            name='member_code',
            field=models.CharField(blank=True, default='', max_length=10),
        ),
        migrations.AddField(
            model_name='committeemember',
            name='qr_token',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        migrations.AddField(
            model_name='snackclaim',
            name='qr_token_used',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.RunPython(backfill_codes_and_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='committeemember',
            name='member_code',
            field=models.CharField(max_length=10, unique=True),
        ),
        migrations.AlterField(
            model_name='committeemember',
            name='qr_token',
            field=models.CharField(max_length=32, unique=True),
        ),
        migrations.AlterField(
            model_name='snackclaim',
            name='detection_method',
            field=models.CharField(
                choices=[('QR', 'QR'), ('MANUAL', 'Manual')],
                default='QR',
                max_length=10,
            ),
        ),
        migrations.RemoveField(
            model_name='snackclaim',
            name='ocr_confidence',
        ),
        migrations.RemoveField(
            model_name='snackclaim',
            name='ocr_text',
        ),
        migrations.AlterModelOptions(
            name='committeemember',
            options={
                'ordering': ['member_code'],
                'verbose_name': 'Anggota Panitia',
                'verbose_name_plural': 'Anggota Panitia',
            },
        ),
    ]
