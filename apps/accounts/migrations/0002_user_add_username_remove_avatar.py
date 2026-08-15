from django.db import migrations, models


def populate_username(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.all():
        username = user.email.split('@')[0]
        base = username
        counter = 1
        while User.objects.filter(username=username).exclude(pk=user.pk).exists():
            username = f'{base}{counter}'
            counter += 1
        user.username = username
        user.save(update_fields=['username'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='username',
            field=models.CharField(default='temp', max_length=150),
            preserve_default=False,
        ),
        migrations.RunPython(populate_username, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(max_length=150, unique=True),
        ),
        migrations.RemoveField(
            model_name='user',
            name='avatar_url',
        ),
    ]
