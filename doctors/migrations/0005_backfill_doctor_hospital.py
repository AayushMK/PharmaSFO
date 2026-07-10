from django.db import migrations


def backfill_hospitals(apps, schema_editor):
    """Give every doctor without a hospital a 'General Hospital' in their own
    area, so the field can become non-nullable (0006)."""
    Area = apps.get_model("tour_plans", "Area")
    Doctor = apps.get_model("doctors", "Doctor")
    Hospital = apps.get_model("doctors", "Hospital")
    for doctor in Doctor.objects.filter(hospital__isnull=True):
        area, _ = Area.objects.get_or_create(name=doctor.area or "Kathmandu")
        hospital, _ = Hospital.objects.get_or_create(name="General Hospital", area=area)
        doctor.hospital = hospital
        doctor.save(update_fields=["hospital"])


class Migration(migrations.Migration):

    dependencies = [
        ("doctors", "0004_hospital_doctor_hospital_and_more"),
        ("tour_plans", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_hospitals, migrations.RunPython.noop),
    ]
