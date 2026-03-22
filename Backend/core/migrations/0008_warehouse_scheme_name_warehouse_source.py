from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_warehousebooking_booking_slot"),
    ]

    operations = [
        migrations.AddField(
            model_name="warehouse",
            name="scheme_name",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="warehouse",
            name="warehouse_source",
            field=models.CharField(blank=True, default="excel", max_length=40),
        ),
    ]
