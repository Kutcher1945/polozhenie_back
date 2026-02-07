# Generated migration for access_code field

from django.db import migrations, models
import random
import string


def generate_access_codes(apps, schema_editor):
    """Generate unique access codes for existing consultations"""
    Consultation = apps.get_model('consultations', 'Consultation')

    existing_codes = set()

    for consultation in Consultation.objects.all():
        # Generate unique code
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if code not in existing_codes:
                existing_codes.add(code)
                consultation.access_code = code
                consultation.save()
                break


class Migration(migrations.Migration):

    dependencies = [
        ('consultations', '0010_consultation_prescription_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='consultation',
            name='access_code',
            field=models.CharField(
                max_length=6,
                null=True,
                blank=True,
                verbose_name='Код доступа',
                help_text='6-значный код для доступа к консультации'
            ),
        ),
        migrations.RunPython(generate_access_codes, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='consultation',
            name='access_code',
            field=models.CharField(
                max_length=6,
                unique=True,
                verbose_name='Код доступа',
                help_text='6-значный код для доступа к консультации'
            ),
        ),
    ]
