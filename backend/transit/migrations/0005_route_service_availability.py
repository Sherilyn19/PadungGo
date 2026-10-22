from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("transit", "0004_vehicle_class_mixed"),
    ]

    operations = [
        migrations.AddField(
            model_name="route",
            name="service_availability",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("not_flagged", "Not flagged"),
                    ("scarce", "Scarce"),
                ],
                default="not_flagged",
            ),
        ),
    ]