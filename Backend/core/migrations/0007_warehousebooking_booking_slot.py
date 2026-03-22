from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_ivrcall_notification_smslog_review"),
    ]

    operations = [
        migrations.AddField(
            model_name="warehousebooking",
            name="booking_slot",
            field=models.CharField(
                choices=[
                    ("morning", "Morning (06:00-10:00)"),
                    ("afternoon", "Afternoon (10:00-14:00)"),
                    ("evening", "Evening (14:00-18:00)"),
                    ("night", "Night (18:00-22:00)"),
                ],
                default="morning",
                max_length=20,
            ),
        ),
    ]
