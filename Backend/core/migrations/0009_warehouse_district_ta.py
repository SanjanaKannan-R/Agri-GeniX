from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_warehouse_scheme_name_warehouse_source"),
    ]

    operations = [
        migrations.AddField(
            model_name="warehouse",
            name="district_ta",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
