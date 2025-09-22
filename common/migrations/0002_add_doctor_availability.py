# Generated migration for doctor availability feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='doctorprofile',
            name='availability_status',
            field=models.CharField(
                choices=[
                    ('available', 'Доступен'),
                    ('busy', 'Занят'),
                    ('offline', 'Не работает'),
                    ('break', 'На перерыве'),
                ],
                default='offline',
                max_length=20,
                verbose_name='Статус доступности'
            ),
        ),
        migrations.AddField(
            model_name='doctorprofile',
            name='last_seen',
            field=models.DateTimeField(auto_now=True, verbose_name='Последний раз в сети'),
        ),
        migrations.AddField(
            model_name='doctorprofile',
            name='availability_note',
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name='Заметка о доступности'
            ),
        ),
    ]