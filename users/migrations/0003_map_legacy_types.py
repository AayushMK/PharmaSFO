from django.db import migrations

# Old position codes -> new hierarchy codes
LEGACY_MAP = {
    "MR": "MSO",     # Medical Representative -> MSO
    "SGM": "SR_GM",  # Senior General Manager -> Sr. GM
}


def forwards(apps, schema_editor):
    User = apps.get_model("users", "User")
    for old, new in LEGACY_MAP.items():
        User.objects.filter(type=old).update(type=new)


def backwards(apps, schema_editor):
    User = apps.get_model("users", "User")
    for old, new in LEGACY_MAP.items():
        User.objects.filter(type=new).update(type=old)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_alter_user_type"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
