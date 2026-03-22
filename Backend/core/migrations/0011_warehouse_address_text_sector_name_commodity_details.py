from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0010_croplisting_image_warehouse_image_conversation_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="warehouse",
            name="address_text",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="warehouse",
            name="sector_name",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="warehouse",
            name="commodity_details",
            field=models.TextField(blank=True, default=""),
        ),
    ]
