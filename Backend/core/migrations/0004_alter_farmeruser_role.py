from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_warehousebooking"),
    ]

    operations = [
        migrations.AlterField(
            model_name="farmeruser",
            name="role",
            field=models.CharField(
                choices=[
                    ("farmer", "Farmer"),
                    ("buyer", "Buyer"),
                    ("warehouse_owner", "Warehouse Owner"),
                ],
                default="farmer",
                max_length=20,
            ),
        ),
    ]
