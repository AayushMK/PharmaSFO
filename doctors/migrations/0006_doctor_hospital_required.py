import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("doctors", "0005_backfill_doctor_hospital"),
    ]

    operations = [
        migrations.AlterField(
            model_name="doctor",
            name="hospital",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="doctors",
                to="doctors.hospital",
            ),
        ),
    ]
